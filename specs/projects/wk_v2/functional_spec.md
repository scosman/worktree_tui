---
status: complete
---

# Functional Spec: wk v2 — a herdr Docker Sandbox plugin

## Summary

`wk` v2 is a **herdr plugin, written in Go**, with one job: **give every git worktree its own Docker
Sandbox microVM, and make it easy to run things inside it.**

It is a full rewrite. Nothing carries over from v1 — herdr covers ~95% of what v1 did (worktree
list, launching, navigation, persistence), and the remaining slice is the sandbox layer, which v1
never had.

**Reusable** means: install the plugin once, then any repo opts in by committing one config file.

**Division of labour:**

| Concern | Owner |
|---|---|
| Multiplexing, panes, keyboard nav, persistence, remote access | herdr |
| Agent state reporting (working / blocked / idle) | herdr |
| Worktree create / open / list | herdr (native `herdr worktree`) |
| Pane layout — which tabs, which splits, which commands | **a separate layout plugin** (not ours) |
| **Sandbox lifecycle** | **`wk`** |
| **Port allocation, publishing** | **`wk`** |
| **Running commands inside the sandbox** | **`wk`** |

Layout is deliberately a different plugin. `wk` stays a sandbox plugin; the README documents how to
use it alongside a layout plugin. Existing project configs get ported over one-off.

## How the two plugins compose

The integration point is `wk exec`. A layout plugin's pane command is written as:

```
wk exec -- npm run dev
```

That is the entire contract. `wk` doesn't know the layout plugin exists, and the layout plugin
doesn't know about sandboxes.

> **Architecture question:** if herdr allows setting a default shell/command wrapper per workspace,
> `wk` could sandbox *every* pane transparently and the `wk exec --` prefix would disappear from
> layout configs. That is a strictly nicer UX. To be investigated in the architecture step; the
> explicit prefix is the fallback and is always available.

## Core Flow

1. User runs `herdr worktree create my-feature` (or uses herdr's worktree UI).
2. herdr creates the worktree, makes a workspace for it, and fires events — which differ by
   creation path, so `wk` hooks several and converges (see architecture).
3. `wk` receives an event and:
   a. reads `<repo>/.config/wk.yml`
   b. creates a sandbox for this worktree (mount, resources, network policy)
   c. runs the project's `setup:` commands inside the sandbox (once, on create)
   d. allocates a free host port for each declared named port and publishes it
   e. records the assignments to state
4. The layout plugin opens its configured tabs/panes; each command runs via `wk exec`.
5. User navigates panes by keyboard and sees agent state in herdr's sidebar.

On an already-provisioned worktree the same entry point converges instead: it starts the sandbox if
stopped and **re-publishes ports**, because published ports do not survive a sandbox restart. This
runs on workspace focus, so a sandbox that died is repaired the next time you look at it.

## Features

### F1. Sandbox lifecycle

- **One sandbox per worktree.** Mandatory — the plugin exists for it; there is no unsandboxed mode.
- Sandbox name is derived deterministically from repo + worktree so it can be found again
  (e.g. `wk-<repo>-<worktree>`), sanitised to sbx's naming rules.
- **Mount:** the **repo root**, with the working directory set to the worktree path inside it. This
  is required, not preferred: a worktree's `.git` is a file pointing at
  `REPO_ROOT/.git/worktrees/<name>`, so mounting only the worktree leaves git broken inside the VM.
- **Accepted consequence:** a worktree is *not* isolated from its own project. Its sandbox can see
  and write to the main checkout and sibling worktrees. Everything outside the repo — `~/.ssh`,
  documents, other repos — stays unreachable, and credentials stay host-side. This is the agreed
  isolation bar.
- Resources (`memory`, `cpus`) come from config. **`wk` always passes them explicitly**, because
  sbx's default is 50% of host RAM with no swap and hard OOM kills — a default sized for one
  sandbox, not for running many in parallel.
- Network allow-list from config is applied per sandbox.
- `setup:` commands run inside the sandbox on creation only (dependency install, `.env` copy, etc).

### F2. Ports

**P1 — declare, allocate, publish**

- Config declares **named ports**, each bound to a fixed in-sandbox port:

  ```yaml
  ports:
    WEB: 8000
    BACKEND: 3000
  ```

- The in-sandbox port is fixed and identical across worktrees. Each sandbox has its own network
  namespace, so there is no collision and **project config never changes per worktree**.
- `wk` allocates a **free host port per name per worktree** and publishes it
  (`sbx ports <sandbox> --publish <hostport>:<sandboxport>`).
- Host ports are allocated **deterministically where possible** — derived from repo + worktree +
  name so a given worktree keeps a stable, bookmarkable URL across restarts — falling back to the
  next free port on collision.
- Re-published automatically on workspace open / sandbox restart, since published ports do not
  survive a stop.
- `wk ports` prints the current assignments on demand.
- **Binding check:** a service bound to `127.0.0.1` inside the sandbox is unreachable through a
  published port. `wk` detects the common failure (port published, nothing answering) and names
  `0.0.0.0` as the fix, rather than leaving a dead link.

**P2 — ergonomics**

- Print the port assignments at workspace startup, as clickable terminal links (OSC 8 hyperlinks,
  plain URLs where unsupported).
- Inject the assignments as env vars into everything run through `wk exec`, so `echo $WEB_PORT`
  works. Per name three vars: `WEB_PORT` (host port), `WEB_URL` (`http://localhost:<hostport>`),
  and `WEB` as an alias of the URL, so `open $WEB` works.

### F3. `wk exec` — the sandbox shim

The single mechanism that makes everything else composable:

```
wk exec -- npm run dev
```

- Resolves which worktree/sandbox it is in from its working directory.
- **Waits** for the sandbox to be ready (bounded timeout), so panes can launch immediately without
  racing sandbox creation. This removes any ordering dependency between `wk` and the layout plugin.
- Runs the command inside the sandbox via `sbx exec`, with the working directory mapped to the
  worktree (and, in P2, port env vars injected).
- Streams stdio through transparently and **propagates the exit code**.
- For agent panes, sets `HERDR_AGENT=<agent>` so herdr picks the right screen manifest — without it,
  herdr's process detection sees `sbx`, not `claude`, and reports nothing.

### F4. Agent state through the sandbox boundary

Expected behaviour with an agent running via `wk exec`:

| Layer | Works? |
|---|---|
| herdr screen manifests (output parsing) | Yes — the agent renders through the pane's PTY |
| herdr process detection | Only via `HERDR_AGENT` (F3) |
| herdr semantic hook integration | Likely not — the hook targets a host Unix socket absent inside the VM |

v1 ships the degraded-but-working version: `HERDR_AGENT` + screen manifests. Bridging the socket
into the sandbox is **out of scope for v1**, revisited only if the degraded version proves annoying.

### F5. Configuration

One file per project, committed to the repo: **`.config/wk.yml`**.

```yaml
sandbox:
  memory: 8g
  cpus: 4
  allow_network:
    - "*.npmjs.org"
    - "api.mycompany.com"
  setup:
    - npm install

ports:
  WEB: 8000
  BACKEND: 3000

agents:
  claude: claude          # pane command -> HERDR_AGENT value
```

- Absent file → the repo is not `wk`-managed; the plugin does nothing and stays silent.
- Absent `ports` → no publishing; everything else still applies.
- Unknown keys are an error, not a silent ignore — a typo'd `memroy` must not quietly hand back a
  32 GiB sandbox.

### F6. CLI surface

The plugin is also a CLI (herdr plugins invoke their own binary; the herdr CLI *is* the plugin API).

| Command | Purpose |
|---|---|
| `wk exec -- CMD` | Run CMD inside this worktree's sandbox (F3) |
| `wk up` | Create/start sandbox, publish ports — what `worktree.created`/`opened` calls |
| `wk down` | Stop this worktree's sandbox |
| `wk rm [path]` | Tear down the sandbox for a removed worktree — what `worktree.removed` calls |
| `wk gc` | Remove sandboxes whose worktree no longer exists (safety net) |
| `wk ports` | Print current assignments; re-publish if needed |
| `wk status` | Sandbox state, resources, published ports for this worktree |
| `wk doctor` | Verify `herdr` and `sbx` are installed and the plugin is linked |

## Errors

Failure handling is opinionated toward *never silently degrading isolation*:

- **`sbx` or `herdr` missing** → clear message with install instructions; `wk doctor` covers it.
- **Sandbox creation fails** → the workspace still opens, panes show the error. Panes must not fall
  back to running on the host. Isolation is mandatory, and a silent host fallback is the single
  worst outcome available here — it is exactly the sbx `--branch` bug (#127), with agents in YOLO
  mode.
- **Port allocation exhausted / host port taken** → fail that port with a named error; other ports
  and the sandbox still come up.
- **Sandbox OOM-killed** → surface it as such in `wk status`, and name the `memory:` config key.
  sbx has no swap, so this is a hard kill with no warning.
- **Config parse error / unknown key** → fail loudly with the file path and line, do nothing else.
- **`wk exec` outside a known worktree** → clear error, non-zero exit.

## Out of Scope (v1)

- Layout — a separate plugin's job; README documents interop
- TUI of any kind — herdr provides it
- Remote access, persistence, session management — herdr provides it
- Worktree create/remove/list UX — herdr provides it
- worktrunk integration (revisit if herdr-native worktrees lack needed hooks)
- Bridging herdr's semantic agent-state socket into the sandbox (F4)
- Non-Claude agents beyond the generic `HERDR_AGENT` mapping
- Windows support (Linux/macOS only, following sbx availability)

## Resolved Questions

1. **Default command wrapper / shell per workspace?** No — herdr's terminal defaults (shell
   executable, shell mode, cwd policy) are **global config**, not per-workspace. Overriding the
   shell globally to sandbox panes would hit every project and every pane, which is far too blunt.
   **Decision: the explicit `wk exec --` prefix stands, and `wk shell-init` stays deferred.**

2. **Worktree removed event?** Yes — `worktree.removed`. Important caveat: **it fires after the
   worktree directory is already deleted**, so the handler cannot resolve identity from the path on
   disk and must look it up from recorded state. `wk`'s state file already stores that mapping.

3. **Hooks on `herdr worktree create`?** Events are the only entry point — but the event set is
   **not uniform across creation paths**, which is the significant finding:

   | Creation path | Events emitted |
   |---|---|
   | `herdr worktree create` (CLI) | `worktree.created` + `workspace.created` |
   | herdr UI "new worktree" | **only `workspace.focused`** |

   Hooking `worktree.created` alone means **worktrees created from the herdr UI never get a
   sandbox** — and the UI is the path most likely to be used day to day. This changes the design;
   see architecture.

4. **Is `sbx ssh` stable?** Yes — SSH is in stable releases (`sbx setup ssh`, and v0.38.0 carries
   SSH session fixes), not nightly-only. Not adopted for v1: `wk exec` is already specified and
   works, and switching the execution mechanism is a bigger change than the marginal gain in
   process detection. Recorded as a future option.

5. **sbx Linux support?** Partial: **Arm Linux from sbx 0.33+**, using KVM, requiring Ubuntu 24.04+
   on aarch64 on bare metal. macOS and Windows remain the primary platforms. Fine for a
   macOS-first personal tool; noted in case this ever needs to run on a Linux box.

## Open Questions

None blocking. Remaining verification is behavioural — how noisy `workspace.focused` is in practice,
and whether screen-manifest agent detection through `sbx` is good enough in daily use (F4).
