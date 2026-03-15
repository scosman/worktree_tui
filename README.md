# Worktree TUI

This is an interactive TUI for managing git worktrees.

It's uses the excellent [Worktrunk](https://worktrunk.dev) project for operations, just adding a TUI layer.

## Preview

![wt_420](https://github.com/user-attachments/assets/29fb7ed5-f090-405a-ad86-44e93b74f2ec)

Note: this demo also shows a [zellij](https://zellij.dev) based "launch command". See how to configure a launch command below.

## Installing and Setup

```
# Install UV if you don't already have it: https://docs.astral.sh/uv/getting-started/installation/

# Install and configure worktrunk (dependency)
brew install worktrunk
wt config shell install

# Install this project (`wk` command)
uv tool install "git+https://github.com/scosman/worktree_tui"

# Run `wk` command. First launch will ask you to update .zshrc
wk
```

## Project Configuration

You can add custom commands to a config file in your project root, which will extend the features in the TUI:

File `.config/wk.yml`

 - open_workspace_cmd: the "launch workspace" command. If missing, launch option won't appear in TUI. Useful for tools like tmux/zellij.
 - restart_workspace_cmd: the "launch workspace" command. If missing, restart option won't appear in TUI
 - custom_commands: a set of custom commands you can invoke from the TUI

```yaml
open_workspace_cmd: tmux ...
restart_workspace_cmd: tmux delete ... & tmux ...

custom_commands:
  t:
    name: Test
    command: npm test
```
