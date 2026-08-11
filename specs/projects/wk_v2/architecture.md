---
status: draft
---

# Architecture: wk v2

Go 1.24 CLI + herdr plugin. Single static binary named `wk`, shipped with a `herdr-plugin.toml`.

**Design stance:** this is a personal utility that shells out to two other tools. The whole risk
surface is (a) getting identity/naming right, (b) not racing on port allocation, and (c) never
silently running on the host when the sandbox failed. Everything else is plumbing, and the
architecture optimises for testability of those three things.

## Dependencies

| Dep | Why |
|---|---|
| `gopkg.in/yaml.v3` | config parsing, with `KnownFields(true)` for strict unknown-key errors |
| `golang.org/x/sys` | `flock` for the port-allocation lock |
| stdlib `flag` + manual dispatch | 6 subcommands; cobra is not worth the dependency here |

No other third-party deps. `sbx`, `git`, and `herdr` are invoked as subprocesses.

## Package Layout

```
cmd/wk/main.go            # arg dispatch, exit codes, slog setup
internal/config/          # .config/wk.yml parse + validate
internal/gitutil/         # repo root, worktree resolution (Git interface)
internal/naming/          # slugging, sandbox names (pure, no I/O)
internal/ports/           # deterministic allocation + probing
internal/state/           # per-worktree state file, locking
internal/sandbox/         # Sandboxer interface, sbx CLI impl, fake
internal/herdr/           # Herdr interface via HERDR_BIN_PATH
internal/app/             # command implementations (up/down/exec/ports/status/doctor/gc)
```

`internal/naming` and `internal/ports` are pure functions over inputs — the parts most worth
testing, and testable with zero mocking.

## The Three External Boundaries

Every external tool sits behind an interface so `internal/app` is testable without Docker, git, or
herdr installed. **No business logic calls `exec.Command` directly.**

```go
// internal/sandbox
type Sandboxer interface {
    Create(ctx context.Context, spec CreateSpec) error
    Status(ctx context.Context, name string) (Status, error)  // NotFound is a value, not an error
    Start(ctx context.Context, name string) error
    Stop(ctx context.Context, name string) error
    Exec(ctx context.Context, name string, opts ExecOpts) (exitCode int, err error)
    PublishPort(ctx context.Context, name string, hostPort, sandboxPort int) error
    AllowNetwork(ctx context.Context, name string, resources []string) error
}

type CreateSpec struct {
    Name       string
    MountPath  string   // repo root
    WorkDir    string   // worktree path, inside the mount
    Memory     string
    CPUs       int
}

type ExecOpts struct {
    Argv    []string
    WorkDir string
    Env     map[string]string
    Stdin   io.Reader
    Stdout  io.Writer
    Stderr  io.Writer
    TTY     bool
}

type Status struct {
    State     State // NotFound | Stopped | Starting | Running
    OOMKilled bool
}
```

Implementations: `sbx.CLI` (shells out) and `sandbox.Fake` (in-memory, used by all app tests).

`gitutil.Git` and `herdr.Client` follow the same shape.

## Data Model

### Identity resolution

Given a working directory, `wk` resolves:

| Field | How |
|---|---|
| Worktree root | `git rev-parse --show-toplevel` |
| Main repo root | parent dir of `git rev-parse --path-format=absolute --git-common-dir` |
| Worktree name | basename of worktree root (main checkout → repo basename) |
| Config path | `<worktree root>/.config/wk.yml` |

Config is read from the **worktree**, not the main checkout, so a branch can change its own sandbox
config and the change takes effect on that worktree only.

The **mount is the main repo root; the working directory is the worktree path inside it.** This is
forced by git: a worktree's `.git` is a file pointing at `MAIN/.git/worktrees/<name>`, so mounting
only the worktree leaves git non-functional inside the VM.

### Sandbox naming

Pure function in `internal/naming`:

```go
func SandboxName(repoRoot, worktreePath string) string
```

- slug = lowercase, `[^a-z0-9-]` → `-`, collapse repeated `-`, trim `-`
- name = `wk-<repoSlug>-<worktreeSlug>`
- if `len(name) > 48`: truncate the two slugs proportionally and append `-<h>` where `h` is the
  first 6 hex chars of SHA-256 over the full `repoRoot + "\x00" + worktreePath`
- **always** append the hash suffix when truncation occurred, never otherwise (stable short names
  in the common case, collision-safe in the long case)

Deterministic and I/O-free, so it is fully table-testable — including unicode, very long branch
names, and two different repos with the same basename.

### State

One JSON file per worktree at `$XDG_STATE_HOME/wk/<sandbox-name>.json` (default
`~/.local/state/wk/`). Never inside the repo.

```go
type State struct {
    Version      int               // schema version, currently 1
    SandboxName  string
    RepoRoot     string
    WorktreePath string
    Phase        Phase             // Provisioning | Ready | Failed
    FailureMsg   string            // populated when Phase == Failed
    Ports        map[string]PortAssignment  // keyed by config port name
    UpdatedAt    time.Time
}

type PortAssignment struct {
    SandboxPort int
    HostPort    int
}
```

`Phase` is the coordination mechanism between `wk up` and `wk exec` — see below. Writes are
atomic: write to `<name>.json.tmp`, `fsync`, `rename`.

Unknown `Version` → treat as absent and re-provision, rather than misparsing.

## Key Flows

### `wk up` (invoked by `worktree.created` / `worktree.opened`)

1. Resolve identity. No config file → exit 0 silently (repo not wk-managed).
2. Load + validate config. Invalid → write `Phase: Failed` with the message, exit 2.
3. Write state `Phase: Provisioning` **before doing anything slow.** This is what lets panes that
   have already launched know to wait rather than error.
4. `Status(name)`:
   - `NotFound` → `Create`, then `AllowNetwork`, then run `setup:` commands via `Exec`
   - `Stopped` → `Start` (skip setup — it is create-only)
   - `Running` → continue
5. Allocate + publish ports (below).
6. Write state `Phase: Ready` with assignments.
7. On any failure: write `Phase: Failed` with the error, exit non-zero. **Never** leave state as
   `Provisioning`, or panes hang until timeout.

### `wk exec -- CMD`

1. Resolve identity; no config → error (exit 2). `wk exec` in an unmanaged repo is a mistake worth
   surfacing, not something to pass through to the host.
2. Read state, polling with backoff (100ms → 1s, capped) until timeout (default 120s,
   `sandbox.startup_timeout`):
   - absent or `Provisioning` → keep waiting (absent is the *normal* state at t=0, when the layout
     plugin's panes launch before the event handler has run)
   - `Failed` → exit immediately, printing the recorded failure. No waiting, no host fallback.
   - `Ready` → proceed
3. Build env: `HERDR_AGENT` if the command's first token matches an `agents:` key, plus (P2) the
   port vars `NAME`, `NAME_PORT`, `NAME_URL`.
4. `Exec` with `TTY: true` when stdin is a terminal, streaming stdio straight through.
5. **Exit with the command's exit code.** A pane must reflect what actually happened.

On timeout: exit non-zero with a message naming `wk status` and `wk doctor`. Never run on the host.

### Port allocation

```go
func Derive(repoRoot, worktreePath, portName string, r Range) int
```

- `h = FNV-1a-64(repoSlug + "/" + worktreeSlug + "/" + portName)`
- `candidate = r.Start + int(h % uint64(r.Size))`, default range 20000–39999 (`ports.range` config)
- linear probe `candidate+1`, wrapping within the range, up to 100 attempts

A candidate is accepted when it is (a) not held by another worktree's state file and (b) bindable —
tested by `net.Listen("tcp", "127.0.0.1:<p>")` then immediate close.

**Stability rule:** if state already holds an assignment for this name and it is still bindable,
reuse it. Only re-derive when it is gone. This is what makes URLs bookmarkable across restarts.

**Race handling:** two worktrees starting concurrently can derive the same candidate. Allocation
for the whole set of ports happens under an exclusive `flock` on
`$XDG_STATE_HOME/wk/alloc.lock`, held across "scan other state files → probe → write our state".
The listen-probe is inherently racy against non-`wk` processes; that residual risk is accepted and
surfaces as a publish failure with a clear message, not a corrupt assignment.

Publishing is per port; one failure marks that port failed and continues with the rest, per the
functional spec.

### `wk gc`

Removes sandboxes whose recorded `WorktreePath` no longer exists on disk, and their state files.

This exists because **it is unknown whether herdr fires a worktree-removed event.** Rather than
depend on an unverified hook, cleanup is an explicit command; if the event turns out to exist, the
manifest gains a hook that calls `wk gc` and nothing else changes. Removing the unknown from the
critical path is the point.

## Plugin Integration

`herdr-plugin.toml` declares event hooks mapping to the binary:

```toml
[[hooks]]
on = "worktree.created"
run = "wk up"

[[hooks]]
on = "worktree.opened"
run = "wk up"
```

Per herdr's docs, unknown event names produce a warning at link time rather than a failure, so an
event name that turns out to be wrong degrades to "hook never fires" — detectable via `wk doctor`,
which reports whether the plugin is linked and which hooks herdr acknowledges.

herdr is invoked through `HERDR_BIN_PATH` (not a hardcoded `herdr`), per herdr's plugin guidance.

### Transparent sandboxing — deferred, not designed away

Pane commands run inside the user's interactive login shell. That means a future `wk shell-init`
snippet could re-exec into the sandbox automatically and drop the `wk exec --` prefix from layout
configs. **Not in v1:** it is implicit magic with real recursion hazards (a shell inside the sandbox
must not re-trigger it), and the explicit prefix works. Revisit once the explicit form has been
lived with.

## Error Handling

Typed errors carrying an exit code; `main` maps them and prints one clear line to stderr.

| Code | Meaning |
|---|---|
| 0 | success (including "not a wk repo" for `wk up`) |
| 1 | general failure |
| 2 | config invalid / not a wk-managed repo |
| 3 | sandbox operation failed |
| 4 | preflight failed (`sbx` or `herdr` missing) |
| *n* | `wk exec` propagates the inner command's code |

Logging via `log/slog` to **stderr** at warn+, `--verbose` for debug. Stdout carries only command
output, so `wk ports` stays pipeable.

**The invariant that overrides everything else:** no code path runs a user command on the host when
the sandbox is unavailable. There is exactly one call site for running user commands (`Sandboxer.
Exec`), and a test asserts no `exec.Command` outside `internal/sandbox` and `internal/gitutil`.

## Testing Strategy

Standard library `testing`, table-driven. No mocking framework — the interfaces are small enough to
hand-write fakes.

| Package | Approach |
|---|---|
| `naming` | Pure table tests: long names, unicode, truncation+hash, two repos sharing a basename |
| `ports` | Determinism (same input → same port), probe/wrap/exhaustion, stability-reuse, concurrent allocation under flock via goroutines + temp dirs |
| `config` | Golden valid configs; unknown-key and type errors assert message includes path and field |
| `state` | Atomic write, corrupt/partial file, unknown version → re-provision |
| `app` | Full flows against `sandbox.Fake` + fake git: up-creates, up-restarts-skips-setup, failure writes Failed phase, exec waits then runs, exec-on-Failed exits fast, exec propagates exit code |
| `doctor`/`gc` | Fakes reporting missing binaries; gc with a state file pointing at a deleted path |

Integration tests behind `//go:build integration`, requiring real `sbx` — run manually, not in CI.

Coverage target: high on `naming`, `ports`, `config`, `state` (pure/near-pure); `app` covered by
flow tests; no target on the CLI-shelling implementations, which are exercised by integration tests.

## Repo Changes

This replaces the Python project in place:

- delete `src/wk/`, `tests/`, `main.py`, `pyproject.toml`, `uv.lock`, `.python-version`
- add `go.mod` (module `github.com/scosman/worktree_tui`), `cmd/`, `internal/`
- rewrite `checks.sh` for Go: `gofmt -l`, `go vet`, `golangci-lint run`, `go test ./...`
- update `CLAUDE.md` commands section to match
- v1's `specs/*.md` (flat layout) describe the old project; leave them, they are history

## Single Doc Decision

This is a small project — 7 packages, 7 commands, ~2 non-trivial algorithms. Everything fits here;
**no separate component docs.**
