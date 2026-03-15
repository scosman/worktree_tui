# Worktree TUI

This is an interactive TUI for managing git worktrees.

It's uses the excellent [Worktrunk](https://worktrunk.dev) project for operations, just adding a TUI layer.

## Preview


## Installing and Setup

```
# Install UV if you don't already have it: https://docs.astral.sh/uv/getting-started/installation/

# Install `wk` command
uv tool install "git+https://github.com/scosman/worktree_tui"

# Run `wk` command. First launch will ask you to update .zshrc
wk
```

## Project Configuration

You can add custom commands to a config file in your project root, which will extend the features in the TUI:

File `.config/wk.yml`

 - OPEN_WORKSPACE_CMD: the "launch workspace" command. If missing, launch option won't appear in TUI
 - RESTART_WORKSPACE_CMD: the "launch workspace" command. If missing, restart option won't appear in TUI
