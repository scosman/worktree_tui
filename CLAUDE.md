# Key Files

specs/phase_instructions.md - How to implement a "phase" of a project. Start here.
specs/implementation_plan.md — Build checklist (track progress here)
specs/spec_and_architecture.md — Full specification and component design

## Commands & Tools

You have access ot a MCP server to running tools like lint, format, types, test.

We use:
 - ruff for formatting: `uvx ruff format` to fix issues
 - ruff checking: `uvx ruff check --fix` to fix issues
 - ty for typechecking: `uvx ty check` to run

This script will run all checks (lint, format, types, tests):
```bash
uv run ./checks.sh
```

Run tests only:
```bash
uv run pytest .
```