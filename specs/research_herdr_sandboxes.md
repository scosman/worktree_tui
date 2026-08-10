# Research: herdr + Docker Sandboxes + `wk`

**Date:** 2026-08-10
**Question:** Can we combine (1) the per-project zellij workspace from `wk`, (2) herdr's agent
state reporting / remote access / persistent server, and (3) Docker Sandboxes' isolation — into
one sane setup?

**Short answer:** Yes, but not by keeping all three layers as they are today. One of the three
has to give, and it is the zellij layer. Details in [Conflict 1](#conflict-1-zellij-vs-herdr--mutually-exclusive).

> **Confidence note.** `herdr.dev`, `docs.docker.com` and `deepwiki.com` are all blocked by this
> environment's egress proxy. Facts below come from the docker.com product page and launch blog,
> the herdr GitHub README, and search-engine summaries of the blocked docs. Items marked
> **[verify]** are inferences or single-source claims that should be confirmed on your machine
> before being designed around.

---

## 1. What each piece actually is

### herdr

- Single Rust binary, client/server. **The server owns the PTYs**; clients attach and detach.
  Sessions survive terminal close, network loss, and restarts.
- **AGPL-3.0.** Free for personal use and internal company tooling. A commercial license is only
  needed to distribute a modified herdr as an external SaaS. Freemium business model, paid tier
  details not public.
- **State detection, two layers:**
  1. *Process detection* — which agent binary is running in the pane.
  2. *Screen manifests* — TOML rules that parse terminal output for semantic states (permission
     prompt, task complete, etc).
  Plus an optional third: **official integrations report semantic state directly over the socket**.
  `herdr integration install claude` writes `hooks/herdr-agent-state.sh` and adds hook entries to
  Claude Code's `settings.json`; the hook reports session identity and state transitions.
- State rolls up hierarchically: **agent → pane → tab → workspace**, with `blocked` as the
  highest-priority state. That is the sidebar you want.
- **Socket API:** newline-delimited JSON over a local Unix socket. Exposes `workspace`, `tab`,
  `pane`, `output`, `wait`, `worktree`, and `agent` methods. Agents can spawn panes, read other
  panes' output, and subscribe to state-change events.
- **Agents inherit env:** `HERDR_ENV`, `HERDR_PANE_ID`, `HERDR_BIN_PATH`, `HERDR_SOCKET_PATH`.
  Setting `HERDR_AGENT=<agent>` on a wrapper command forces which screen manifest to use — this
  turns out to matter a lot (see [Conflict 3](#conflict-3-state-detection-across-the-microvm-boundary)).
- **First-class git worktrees.** `herdr worktree create` / `open` makes a fresh workspace for the
  worktree and fires a `worktree.created` or `worktree.opened` event.
- **Plugins:** `herdr-plugin.toml` manifest declares actions, event hooks, managed panes, and link
  handlers. There is no separate SDK — *the herdr CLI is the plugin API*, and plugins should invoke
  it via `HERDR_BIN_PATH`. Link with `herdr plugin link "$PWD"`; relink after manifest edits.
- **Remote access:** two models — ssh directly to the box and run herdr there (the TUI adapts to
  narrow/phone screens), or run local herdr as a thin client that attaches to a remote herdr server
  over ssh and streams the UI back. No official web UI or mobile app. Third-party `herdr-remote`
  adds menu bar / phone / Telegram monitoring with a tunnel.

**The ecosystem already overlaps your project heavily.** Existing plugins:

| Plugin | What it does | Overlaps `wk`? |
|---|---|---|
| `herdr-plugin-workspace-manager` | Declarative tab/pane/split/env/per-pane startup commands in YAML, applied automatically per repo when a worktree is created | **Yes — this is your `open_workspace_cmd`** |
| `herdr-plus` | Worktree auto-layout; catches `worktree.created`/`opened`, opens layout tabs/panes with commands running. Layouts in `~/.config/herdr-plus/worktrees/*.toml` | **Yes — same** |
| `herdr-plugin-git-worktree-hooks` | Shell commands on worktree create/remove; one YAML for all projects, `$PROJECT`/`$MAIN`/`$WORKTREE`/`$EVENT` in env | Partly (worktrunk hooks) |
| `herdr-worktrunk` | **Integrates worktrunk for worktree management** | **Yes — your exact dependency** |
| `herdr-sessionizer` | Fuzzy-open projects/worktrees into declarative TOML layouts, per-repo overrides | Yes — your TUI's job |

That is worth sitting with: the parts of `wk` that are *worktree list + launch a per-project
layout* already exist, several times over, in the herdr plugin ecosystem — so that's code you may
be able to simply not write.

### Docker Sandboxes (`sbx`)

- **microVM per sandbox**: own kernel, own filesystem, own Docker daemon, shell agent tooling. The
  host filesystem is unreachable outside the mounted workspace. Outbound traffic goes through a
  proxy enforcing an explicit allow-list. **Credentials stay on the host**, not in the VM.
- `sbx run claude` — downloads the agent image, creates a sandbox **named after the current
  working directory**. Claude Code is launched in `--dangerously-skip-permissions` (YOLO) mode by
  default, which is the entire point.
- `sbx` with no args opens a **dashboard**: every sandbox, its state, live CPU/memory, and a
  Network panel showing a live log of outbound connections you can allow/block.
- **Other commands:**
  - `sbx exec -it <name> bash`, `sbx exec -d <name> npm start`, `sbx exec -u root <name> ...`
  - `sbx ssh` / `ssh <name>.sbx` — proper SSH bridge (nightly builds) **[verify: may still be nightly-only]**
  - `sbx ports <name> --publish [HOST_IP:]HOST_PORT:SANDBOX_PORT[/PROTO]`
  - `sbx policy allow network "*.npmjs.org,api.example.com:443"`, `--sandbox <name>` to scope it,
    `sbx policy ls [--wide]`
- **Resources:** default memory is 50% of host RAM (max 32 GiB), **no swap** — hitting the limit
  means OOM-kill with no soft landing. Tunable: `sbx run claude --cpus 4 --memory 8g`. This matters
  a lot if you want many parallel sandboxes; the default is sized for *one*.
- **Customization:** templates (the OCI image the VM boots from), custom Dockerfile, and baking in
  an agent config dir (e.g. `~/.claude` → `/home/agent/.claude`). "Kits" are declarative
  `spec.yaml` files packaging tools + env + security boundaries.
- **Platforms:** macOS and Windows; Linux was "coming" at launch **[verify current status]**.
- **Worktree/branch mode:** `--branch` creates a git worktree under `.sbx/` in your repo, branched
  off your latest commit. Two known sharp edges filed against `docker/sbx-releases`:
  - #127 — creating a sandbox for an **existing** branch errors (`a branch named X already exists`)
    and **silently falls back to mounting the main workspace**. That fallback is the dangerous part.
  - #154 — in worktree mode, **agents can reach uncommitted host files via `../../../`**.

---

## 2. The three hard conflicts

### Conflict 1: zellij vs herdr — mutually exclusive

**Nesting a multiplexer inside a herdr pane disables agent state detection.** This is documented
for tmux ("run agents directly in herdr panes; don't nest tmux inside herdr") and the same
mechanism applies to zellij: to herdr, a zellij pane is one opaque PTY running `zellij`, and both
process detection and screen-manifest parsing see zellij's rendering, not the agent's.

So "keep my zellij workspace, add herdr's status board" is not on the table. herdr's entire value
proposition *is* the state board, and zellij is exactly what blinds it.

**The resolution is a translation, not a loss.** Your zellij layout — a tab for Claude, a tab for
frontend, a tab for backend, each with a startup command — is precisely what
`herdr-plugin-workspace-manager` and `herdr-plus` express declaratively, applied automatically on
`worktree.created`. Your `open_workspace_cmd` string becomes a layout file. You lose zellij; you
keep the workspace concept, and you gain per-pane status.

This is the single biggest decision in the project, and it is mostly a migration task.

**Nuance worth keeping:** the constraint only binds *agent* panes. herdr needs to see Claude's
output to report Claude's state; it does not care what's in your frontend/backend panes. So a
hybrid — agent in a native herdr pane, servers in a zellij tab — is technically fine. It's just
hard to justify: once the layout is expressed as herdr tabs anyway, zellij is carrying no weight.
Treat "keep zellij for servers" as an escape hatch, not the design.

### Conflict 2: worktrees vs sandbox isolation — leaky, and three-way redundant

You would have **three worktree managers** in one stack: worktrunk (what `wk` wraps today), herdr's
native `herdr worktree create`, and `sbx --branch`. Exactly one should own creation; the other two
should observe.

Worse, there is a real technical problem underneath. A git worktree's `.git` is a *file* pointing
at `MAIN_REPO/.git/worktrees/<name>`. So:

- Mount **only the worktree** into the microVM → git is broken inside the sandbox (the gitdir
  pointer dangles). No commits, no diffs, no branch ops.
- Mount **enough to fix that** → you have mounted the parent repo, including every other worktree
  and all your uncommitted host work. That is issue #154, and it means **worktree + sandbox today
  gives you less isolation than the marketing implies**.

**How bad is the leak, exactly?** It is bounded by the mount. The blast radius is *the git project*:
the main checkout, sibling worktrees, and uncommitted work in them. The rest of the host filesystem
— `~/.ssh`, `~/Documents`, other repos — stays unreachable, because sbx mounts only the workspace
and the microVM has no other view of the host. Credentials are held on the host side of the proxy
rather than inside the VM. So the honest summary is: **a worktree is not isolated from its own
project, but the project is still isolated from everything else.** If project-level blast radius is
acceptable, this stops being a blocker and becomes a footnote.

Two clean resolutions if you ever want tighter than that:

- **(a) Sandbox the repo root; do worktrees inside the sandbox.** One microVM per project, `wt`
  and all worktrees live inside it. Git works normally, worktrunk hooks work normally, isolation
  boundary is the project. Downside: worktrees in one project share a blast radius, and the "many
  parallel agents" story becomes many panes in one VM rather than one VM per agent.
- **(b) One sandbox per worktree, sandbox owns the worktree.** Use `sbx --branch` (or clone mode)
  and let the sandbox create its own working copy. Maximum isolation, and it's what sbx is designed
  for. Downside: worktrunk stops being the worktree owner, you inherit #127's silent fallback, and
  your existing hooks/setup story has to move into the sandbox template.

(a) is the pragmatic one and preserves the most of what you have. (b) is the isolation-pure one.
This is a genuine fork in the design and deserves an explicit decision.

### Conflict 3: state detection across the microVM boundary

If a herdr pane runs `sbx run claude`, what does the sidebar show?

| Detection layer | Survives the microVM boundary? |
|---|---|
| Process detection | **No** — the foreground process on the host is `sbx`, not `claude`. **Fix:** set `HERDR_AGENT=claude` on the wrapper command; this is exactly what that env var is for. |
| Screen manifests | **Yes** — Claude's TUI renders through the sandbox's PTY into the herdr pane, so the output rules still match. |
| Semantic hook integration | **Probably not [verify]** — the hook posts to `HERDR_SOCKET_PATH`, a *host* Unix socket. Inside the microVM that socket does not exist, and sbx mounts only the workspace. |

So the honest expectation is **degraded-but-working status**: `HERDR_AGENT` + screen manifests get
you working/blocked/idle; you lose the crisp hook-driven transitions unless the socket is bridged.

Bridging it looks very doable if the degraded version turns out to annoy you: forward the herdr
socket into the sandbox (a mount, or an in-VM shim that calls back to the host over a published
port), install the herdr hook inside the sandbox template, and point it at the shim. Worth trying
the degraded version first — screen manifests may be entirely good enough in practice.

---

## 3. Ports: the same problem, moved somewhere better

Today you generate unique ports per worktree so parallel workspaces don't collide.

With one sandbox per worktree, **each sandbox has its own network namespace**. So the *inside* port
can be fixed and canonical — every worktree's backend is `8000`, every frontend is `3000`, and the
project's own config never changes per worktree. But you still need **unique host ports**, because
you open the web app in a browser on the host. The allocation logic doesn't go away; it moves from
"rewrite the project's config per worktree" to "pick free host ports and publish them", which is
the better place for it.

Gotchas to own:

1. Dev servers must bind `0.0.0.0`, not `127.0.0.1`, or publishing does nothing. Most default to
   `127.0.0.1`.
2. **Published ports do not survive a sandbox stop/restart.** Something has to re-publish them.

**Nice-to-have (P2):** declare N *named* ports in config, allocate + publish them on workspace
start, and print the resulting host URLs in the terminal as clickable links. Worth deciding whether
this belongs here or stays in a single project's config — it's generic enough to live in the tool.

---

## 4. Where does `wk` land?

Given the plugin ecosystem already covers "list worktrees + launch a per-project layout", the
question is how little you can get away with writing. Three options:

**Option A — `wk` becomes a herdr plugin.** *(recommended)*
herdr owns multiplexing, state, persistence, remote. worktrunk (via `herdr-worktrunk`, or your own
hook) owns worktrees. `wk` becomes a `herdr-plugin.toml` that hooks `worktree.created` and owns the
opinionated glue: **sandbox lifecycle, host-port allocation and re-publishing, network allow-list
per project, and the state-across-the-boundary bridge.**
- Pro: you stop maintaining a TUI and a multiplexer integration; you inherit herdr's UI, remote
  access, and persistence for free. This is the "I don't want to maintain mine" outcome you named.
- Con: it means deleting most of the current Textual TUI. That's the real cost.

**Option B — `wk` keeps its TUI, drives herdr over the socket API.**
Keep your keyboard UX; herdr becomes the backend runtime instead of zellij.
- Pro: you keep the UX you like and the code you've written.
- Con: two UIs over the same state, and you maintain the socket-API client forever. herdr's sidebar
  is the thing you wanted from herdr in the first place, so this partly defeats the point.

**Option C — `wk` becomes purely a sandbox + ports orchestrator.**
Drop worktree management and layouts entirely (herdr plugins do those); `wk` is only the sbx layer.
- Pro: smallest possible surface, no overlap with anything.
- Con: it's a thin enough tool that it may not need to be a tool.

**Recommendation: A**, scoped tightly. The parts worth keeping are *sandbox lifecycle + ports +
(maybe) the boundary state bridge* — the things neither herdr nor sbx does, and the things needed
to make them work together. The worktree-list TUI is the part herdr already gives you.

---

## 5. Proposed shape

Target stated for v2: **do less, be more powerful, reusable across projects by dropping a config
into each repo.** That maps onto herdr's model almost exactly:

> **The plugin installs once, globally. The config lives per repo.**

That one sentence is the reusability requirement. A herdr plugin is linked once
(`herdr plugin link`), hooks `worktree.created` / `worktree.opened`, and on each event reads
`<repo>/.config/wk.yml` from the worktree it was handed. Add the file to a project, that project
gets sandboxes + layout. No per-project installation.

### One plugin or two?

The two concerns — *layout* and *sandbox* — look separable, but they are coupled at exactly the
point that matters:

- every layout pane must run **inside** the sandbox (`sbx exec`, not a bare shell),
- every server pane's port must be **published** to a host port and reported back to you,
- the agent pane needs `HERDR_AGENT=claude` **because** it's wrapped in `sbx`.

Split them into two plugins and you have to invent a coordination protocol between them for no
benefit. **Recommend one plugin** that owns the pipeline `worktree → sandbox → layout → ports`.

Note also that the layout half is *already served* by `herdr-plugin-workspace-manager` and
`herdr-plus`. Before writing it, check whether either can express your layouts (open question 7).
If one can, the plugin shrinks to the sandbox half plus a thin layout delegation — which is the
best possible outcome for "does less itself."

**Do not wrap the herdr server.** It's the one option that reacquires everything you're trying to
stop maintaining — persistence, attach/detach, session state — and puts you in a permanent race
with herdr's releases. Plugin, not wrapper.

### Sketch: `.config/wk.yml` v2

```yaml
sandbox:
  enabled: true
  memory: 8g          # explicit — the sbx default is 50% of host RAM, sized for ONE sandbox
  cpus: 4
  allow_network:      # -> sbx policy allow network --sandbox <name>
    - "*.npmjs.org"
    - "api.mycompany.com"

layout:
  tabs:
    - name: agent
      agent: claude   # -> HERDR_AGENT=claude, so state detection survives the sbx wrapper
      command: claude
    - name: backend
      command: npm run dev
      port: 8000      # canonical port INSIDE the sandbox
    - name: frontend
      command: npm run web
      port: 3000
```

Note what disappears: **no per-worktree port rewriting.** Each sandbox has its own network
namespace, so every worktree's backend can be `8000` internally; `wk` only allocates unique *host*
ports at publish time and tells you where they landed. The unique-port generation logic in today's
`wk` is deleted, not ported.

### What v2 keeps, and what it deletes

| Today | v2 |
|---|---|
| Textual TUI, worktree list widget, theme | **Deleted** — herdr's sidebar and worktree UI replace it |
| Shell wrapper (`__WK_WRAPPED`, stdout-eval `cd`) | **Deleted** — herdr owns pane cwd; no parent-shell `cd` needed |
| `wt` wrapping / worktree CRUD | **Delegated** — herdr worktree events, worktrunk still does setup hooks |
| `open_workspace_cmd` / `restart_workspace_cmd` | **Becomes** the declarative `layout:` block |
| Unique port generation | **Adapted** — same allocation, now applied to host ports via `sbx ports --publish`; the in-sandbox port becomes fixed |
| `custom_commands` | **Kept** — maps to plugin `actions` in `herdr-plugin.toml` |
| — | **New:** sandbox lifecycle, port publish/re-publish on restart, network policy, state bridge |

That is a large deletion, and it is the point: the surviving code is the glue that neither herdr
nor sbx provides.

---

## 6. Open questions to verify locally

These couldn't be settled from here (blocked docs) and each one could move the design:

1. **Does the herdr Claude hook work from inside a sandbox?** Run `sbx run claude` in a herdr pane
   and watch the sidebar. This determines whether the socket-bridge work in Option A is needed or
   already solved.
2. **Is `sbx ssh` in stable or nightly only?** If stable, an alternative architecture opens up:
   herdr panes ssh into long-lived sandboxes, and the agent process is genuinely the foreground
   process inside — possibly restoring process detection.
3. **Linux support for sbx** — current status, if you ever want this on a Linux box or CI.
4. **Does `sbx --branch` still silently fall back to the main workspace** for existing branches
   (#127)? A silent fallback from "isolated worktree" to "your actual repo" while an agent runs in
   YOLO mode is the worst failure mode in this entire stack.
5. **Memory math for N parallel sandboxes.** Default is 50% of host RAM each with no swap and
   hard OOM kills. Find the real per-sandbox floor for your stack and set `--memory` explicitly;
   the defaults are sized for a single sandbox, not for the parallel workflow this project exists for.
6. **Does herdr's worktree support conflict with worktrunk's?** i.e. does `herdr worktree create`
   bypass worktrunk hooks — and does `herdr-worktrunk` already resolve that?
7. **Layout expressiveness** — can `herdr-plugin-workspace-manager` / `herdr-plus` layouts express
   everything your current zellij layout does (per-pane cwd, env, ordering, restart semantics)?

---

## Sources

- [Docker Sandboxes product page](https://www.docker.com/products/docker-sandboxes/)
- [Docker blog: Run Claude Code and other coding agents unsupervised, but safely](https://www.docker.com/blog/docker-sandboxes-run-claude-code-and-other-coding-agents-unsupervised-but-safely/)
- [Docker docs: sbx policy allow network](https://docs.docker.com/reference/cli/sbx/policy/allow/network/), [sbx ports](https://docs.docker.com/reference/cli/sbx/ports/), [sbx exec](https://docs.docker.com/reference/cli/sbx/exec/), [customizing sandboxes](https://docs.docker.com/ai/sandboxes/customize/)
- [dockersamples/sbx-quickstart](https://github.com/dockersamples/sbx-quickstart)
- [sbx-releases #127 (existing-branch fallback)](https://github.com/docker/sbx-releases/issues/127), [#154 (worktree `../../../` access)](https://github.com/docker/sbx-releases/issues/154), [#56 (memory limits)](https://github.com/docker/sbx-releases/issues/56)
- [herdr GitHub](https://github.com/ogulcancelik/herdr) · [docs](https://herdr.dev/docs/) — [socket API](https://herdr.dev/docs/socket-api/), [plugins](https://herdr.dev/docs/plugins/), [integrations](https://herdr.dev/docs/integrations/), [persistence & remote](https://herdr.dev/docs/persistence-remote/)
- herdr plugins: [workspace-manager](https://github.com/razajamil/herdr-plugin-workspace-manager) · [herdr-plus](https://github.com/cloudmanic/herdr-plus) ([worktree auto-layout](https://herdrplus.com/docs/worktrees/)) · [git-worktree-hooks](https://github.com/freethinkel/herdr-plugin-git-worktree-hooks) · [worktrunk](https://github.com/devashish2203/herdr-worktrunk) · [sessionizer](https://github.com/andrewchng/herdr-sessionizer) · [worktree-lifecycle](https://github.com/qdentity/herdr-worktree-lifecycle) · [herdr-remote](https://github.com/dcolinmorgan/herdr-remote)
- [Herding parallel agents on a remote box with herdr](https://coles.codes/posts/herding-agents-with-herdr/) · [I Gave Up tmux and Zellij for Herdr](https://www.joshfinnie.com/blog/switching-to-herdr/) · [Better Stack: herdr guide](https://betterstack.com/community/guides/ai/herdr-ai-agent/)
- [Running AI agents safely in a microVM using docker sandbox](https://andrewlock.net/running-ai-agents-safely-in-a-microvm-using-docker-sandbox/) · [10 Things You Must Know About Docker Sandboxes](https://www.ajeetraina.com/10-things-you-must-know-about-docker-sandboxes/) · [sbx ssh hands-on](https://www.ajeetraina.com/ssh-straight-into-your-agent-sandboxes-a-hands-on-look-at-sbx-ssh/)
