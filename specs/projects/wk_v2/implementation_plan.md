---
status: draft
---

# Implementation Plan: wk v2

Details live in [`functional_spec.md`](functional_spec.md) and [`architecture.md`](architecture.md).
Each phase ends with `./checks.sh` green.

## Phases

- [ ] **Phase 1: Repo conversion + foundations.** Delete the Python project (`src/wk/`, `tests/`,
      `main.py`, `pyproject.toml`, `uv.lock`, `.python-version`). Add `go.mod`, `cmd/wk` skeleton.
      Rewrite `checks.sh` and the `CLAUDE.md` commands section for Go. Implement `internal/naming`
      and `internal/config` with full table tests.

- [ ] **Phase 2: State + ports.** `internal/state` (atomic write, phase machine, schema version)
      and `internal/ports` (deterministic derive, probe/wrap/exhaustion, stability-reuse,
      allocation under `flock`). Both near-pure; this is where test depth matters most.

- [ ] **Phase 3: External boundaries.** `internal/sandbox` (`Sandboxer` interface, `sbx.CLI`
      implementation, `Fake`), `internal/gitutil`, `internal/herdr`. Includes the test asserting no
      `exec.Command` outside `internal/sandbox` and `internal/gitutil`.

- [ ] **Phase 4: `wk up` / `down` / `status`.** The provisioning flow: phase-marker write, create
      vs start, `setup:` commands, network allow-list, port allocation and publishing, failure
      recording. Flow tests against the fakes.

- [ ] **Phase 5: `wk exec`.** Phase polling with backoff, fast-fail on `Failed`, TTY passthrough,
      exit-code propagation, `HERDR_AGENT` mapping. The no-host-fallback invariant is tested here.

- [ ] **Phase 6: CLI surface, packaging, ergonomics.** `wk ports`, `wk doctor`, `wk gc`;
      `herdr-plugin.toml`; README covering install and layout-plugin interop (`wk exec -- CMD`).
      Then the P2 items: startup port printing with OSC 8 links, port env injection
      (`NAME` / `NAME_PORT` / `NAME_URL`), and `127.0.0.1` dead-link detection.

## Notes

- Phases 1–3 are buildable and testable without `sbx` or `herdr` installed.
- Real-world verification (the five open questions in the functional spec) needs a machine with
  herdr and sbx — expect adjustments after Phase 6.
