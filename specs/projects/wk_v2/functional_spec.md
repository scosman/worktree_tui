---
status: draft
---

# Functional Spec: wk v2

## Summary

`wk` v2 is a **herdr plugin, written in Go**, that gives every git worktree its own Docker Sandbox
microVM and a keyboard-navigable set of panes running inside it, configured by a single file
committed to each project.

It is a complete replacement for v1. The Textual TUI, the zsh wrapper, the `wt` wrapping, and the
worktree list are all deleted — herdr provides those.

**Division of labour:**

| Concern | Owner |
|---|---|
| Multiplexing, panes, keyboard nav, persistence, remote access | herdr |
| Agent state reporting (working / blocked / idle) | herdr |
| Worktree create / open / list | herdr (native `herdr worktree`) |
| Pane layout (which tabs, which splits) | an existing third-party herdr layout plugin |
| **Sandbox lifecycle** | **`wk`** |
| **Port allocation, publishing, env injection** | **`wk`** |
| **Per-project config that drives all of the above** | **`wk`** |

## Core Flow

1. User runs `herdr worktree create my-feature` (or uses herdr's worktree UI).
2. herdr creates the worktree, makes a workspace for it, fires `worktree.created`.
3. `wk` receives the event and:
   a. reads `<repo>/.config/wk.yml`
   b. allocates a free host port for each declared named port
   c. creates a sandbox for this worktree (mount, resources, network policy)
   d. runs the project's `setup:` commands inside the sandbox (once, on create)
   e. publishes the allocated ports
   f. records the assignment so panes and later commands can read it
4. The layout plugin opens the configured tabs/panes. Every pane's command runs through
   `wk exec`, which executes it **inside** the sandbox with the port env vars injected.
5. User navigates panes by keyboard, sees agent state in herdr's sidebar, and opens the web app
   with `open $WEB`.

`worktree.opened` on an existing worktree does the same minus (d): it starts the sandbox if
stopped and **re-publishes ports**, because published ports do not survive a sandbox restart.

## Features

### F1. Sandbox lifecycle

- **One sandbox per worktree.** Mandatory — the plugin exists for it; there is no unsandboxed mode.
- Sandbox name is derived deterministically from repo + worktree so it can be found again
  (e.g. `wk-<repo>-<worktree>`), sanitised to sbx's naming rules.
- **Mount:** the **repo root**, with the pane's working directory set to the worktree path inside
  it. This is required, not preferred: a worktree's `.git` is a file pointing at
  `REPO_ROOT/.git/worktrees/<name>`, so mounting only the worktree leaves git broken inside the VM.
- **Accepted consequence:** a worktree is *not* isolated from its own project. Its sandbox can see
  and write to the main checkout and sibling worktrees. Everything outside the repo — `~/.ssh`,
  documents, other repos — remains unreachable, and credentials stay host-side. This is the agreed
  isolation bar.
- Resources (`memory`, `cpus`) come from config. **`wk` always passes them explicitly**, because
  sbx's default is 50% of host RAM with no swap and hard OOM kills — a default sized for one
  sandbox, not for the parallel workflow this tool exists for.
- Network allow-list from config is applied per sandbox.
- `setup:` commands run inside the sandbox on creation only, and are the replacement for worktrunk's
  create hooks (dependency install, `.env` copy, etc).

### F2. Ports

- Config declares **named** ports with their fixed in-sandbox value:
  `ports: { web: 3000, api: 8000 }`.
- In-sandbox ports are fixed and identical across worktrees — each sandbox has its own network
  namespace, so there is no collision and **project config never changes per worktree**.
- `wk` allocates a **free host port per name per worktree** and publishes it
  (`sbx ports <name> --publish <host>:<sandbox>`).
- **Env injection:** each pane gets `WEB=http://localhost:<hostport>` and `WEB_PORT=<hostport>`
  (uppercased config key), so `open $WEB` works.
- On workspace open/restart, ports are **re-allocated if needed and re-published** — published
  ports don't survive a sandbox stop.
- On startup, `wk` prints the assignments as clickable terminal links (OSC 8 hyperlinks, plain URLs
  when the terminal doesn't support them).
- **Binding check:** a service bound to `127.0.0.1` inside the sandbox is unreachable through a
  published port. `wk` detects the common failure (port published, nothing answering) and emits a
  message naming `0.0.0.0` as the fix, rather than leaving a dead link.

### F3. `wk exec` — the sandbox shim

The single mechanism that makes everything else composable:

```
wk exec -- npm run dev
```

- Resolves which worktree/sandbox it is in from its working directory.
- **Waits** for the sandbox to be ready (bounded timeout), so panes can launch immediately without
  racing sandbox creation. This is what removes any ordering dependency between `wk` and the layout
  plugin.
- Runs the command inside the sandbox via `sbx exec`, with port env vars injected and the working
  directory mapped to the worktree.
- Streams stdio through transparently and **propagates the exit code**.
- For agent panes, sets `HERDR_AGENT=<agent>` so herdr picks the right screen manifest — without
  it, herdr's process detection sees `sbx`, not `claude`, and reports nothing.

### F4. Layout

`wk` does **not** implement layout. Per-project tabs/panes/splits are delegated to an existing herdr
layout plugin (`herdr-plugin-workspace-manager` or `herdr-plus`), whose per-pane commands are
written as `wk exec -- <command>`.

`wk` must therefore work correctly when the layout plugin runs *before*, *after*, or *concurrently*
with sandbox creation — which F3's wait handles.

Requirement on the chosen plugin: per-pane commands, per-pane working directory, and per-pane env.
Choosing between the candidates is an architecture-step decision.

### F5. Agent state through the sandbox boundary

Expected behaviour with an agent running via `wk exec`:

| Layer | Works? |
|---|---|
| herdr screen manifests (output parsing) | Yes — the agent renders through the pane's PTY |
| herdr process detection | Only via `HERDR_AGENT` (F3) |
| herdr semantic hook integration | Likely not — the hook targets a host Unix socket absent inside the VM |

v1 ships the degraded-but-working version: `HERDR_AGENT` + screen manifests. Bridging the socket
into the sandbox is explicitly **out of scope for v1** and revisited only if the degraded version
proves annoying in daily use.

### F6. Configuration

One file per project, committed to the repo: **`.config/wk.yml`** (same location as v1).

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
  web: 3000
  api: 8000

agents:
  claude: claude          # pane command -> HERDR_AGENT value
```

- Absent file → the repo is not `wk`-managed; the plugin does nothing and stays silent.
- Absent `ports` → no publishing, everything else still applies.
- Unknown keys are an error, not a silent ignore — a typo'd `memroy` must not quietly hand back a
  32 GiB sandbox.

### F7. CLI surface

The plugin is also a CLI (herdr plugins invoke their own binary; the herdr CLI *is* the plugin API).

| Command | Purpose |
|---|---|
| `wk exec -- CMD` | Run CMD inside this worktree's sandbox (F3) |
| `wk up` | Create/start sandbox, publish ports — what `worktree.created`/`opened` calls |
| `wk down` | Stop this worktree's sandbox |
| `wk ports` | Print current assignments as links; re-publish if needed |
| `wk status` | Sandbox state, resources, published ports for this worktree |
| `wk doctor` | Verify `herdr` and `sbx` are installed and the layout plugin is linked |

## Errors

Failure handling is opinionated toward *never silently degrading isolation*:

- **`sbx` or `herdr` missing** → clear message with install instructions; `wk doctor` covers it.
- **Sandbox creation fails** → the workspace still opens, panes show the error. Panes must not fall
  back to running on the host. Isolation is mandatory; a silent host fallback is the single worst
  outcome in this design (it is exactly the sbx `--branch` bug, #127).
- **Port allocation exhausted / host port taken** → fail that port with a named error; other ports
  and the sandbox still come up.
- **Sandbox OOM-killed** → surface it as such in `wk status`, and name the `memory:` config key.
  sbx has no swap, so this is a hard kill with no warning.
- **Config parse error / unknown key** → fail loudly with the file path and line, do nothing else.
- **`wk exec` outside a known worktree** → clear error, non-zero exit.

## Out of Scope (v1)

- TUI of any kind — herdr provides it
- Remote access, persistence, session management — herdr provides it
- Worktree create/remove/list UX — herdr provides it
- worktrunk integration (revisit if herdr-native worktrees lack needed hooks)
- Layout implementation (delegated)
- Bridging herdr's semantic agent-state socket into the sandbox (F5)
- Non-Claude agents beyond the generic `HERDR_AGENT` mapping
- Windows support (Linux/macOS only, following sbx availability)

## Open Questions

1. **Two config files per project.** Reusing a layout plugin means each repo carries
   `.config/wk.yml` *and* the layout plugin's file. That is in tension with "add one config to a
   project". See pushback in the review notes.
2. Does herdr fire a **worktree removed/closed** event? If not, `wk down`/sandbox cleanup is manual
   or polled, and stale sandboxes accumulate.
3. Does `herdr worktree create` expose **hooks** for post-create work, or is the `worktree.created`
   event the only entry point?
4. Is `sbx ssh` in a **stable** release? If so, an alternative to `wk exec` exists where the agent
   is genuinely the foreground process inside the VM, which would restore native process detection.
5. Confirm sbx **Linux** support status.
