---
status: draft
---

# wk v2

A new version of worktree_tui that does less itself and is more powerful.

Today's `wk` is my current iteration for agentic dev: many git worktrees, many workspaces. Roughly
one Zellij workspace config per project — one tab for Claude Code, another for the frontend server,
another for the backend, etc. It generates unique ports so I can have many running in parallel.

Two third-party tools now do big pieces of this better than mine, and I don't want to maintain my
versions of them:

- **[herdr](https://herdr.dev)** — a popular server for parallel Claude Code instances with progress
  reporting (agent idle, agent working, etc). Uses git worktrees. Better than mine in a lot of ways.
- **[Docker Sandboxes](https://www.docker.com/products/docker-sandboxes/)** — run `sbx run claude`
  and Claude runs in a sandbox.

This project is an exploration to see if I can get all three working together, in a sane way:

- **from my project:** keep the per-project workspace concept
- **from herdr:** agent progress, remote access, the "server" concept, plugins
- **from Docker Sandboxes:** safety and isolation

## What I want

- **herdr replaces a lot of my one-off worktree work.** It gives me status updates, a server
  concept, and plugins.
- **A Docker Sandbox integration.**
- **Reusable.** The thing I value in worktree_tui is that different projects get different startup
  scripts and workspaces. I want to use this across many projects just by adding a config to those
  projects.

## Format

TBD. Could be a herdr plugin for "zellij workspace" and another for Docker Sandboxes. Could be a
wrapper of the herdr server.

## Notes / open items

- Where the other parts land is still TBD: startup scripts, per-project config, etc.
- **Ports:** the local server inside a sandbox can always be a fixed port, but I want to open the
  web app in a browser, so I need unique *published* ports per worktree. Not sure yet whether that
  belongs in this tool or in an individual project's config. A P2 helper would be nice: generate N
  named ports, publish them on startup, and have the terminal print them as links.
- **Isolation expectations:** a leak bounded to the git project (main checkout, sibling worktrees,
  uncommitted work in them) is fine. What matters is that `~/.ssh`, my documents, and other repos
  stay out of reach.

## Prior research

See [`specs/research_herdr_sandboxes.md`](../../research_herdr_sandboxes.md) for research on what
herdr and Docker Sandboxes actually provide today, and the conflicts between them.
