# Worktree TUI

This is an interactive TUI for managing git worktrees, allowing developing several features in parallel. The `wk` command is all you need to create worktrees, manage worktrees, jump to worktrees, launch workspaces, and more.

It's wraps the excellent [Worktrunk](https://worktrunk.dev) project for worktree operations, adding a TUI (Terminal UI) so you don't need to memorize commands or type branch names.

## Preview

![wt_420](https://github.com/user-attachments/assets/29fb7ed5-f090-405a-ad86-44e93b74f2ec)

Note: this demo also shows a [zellij](https://zellij.dev) based "launch command" designed for a project with tabs for terminal, claude code, backend server and frontend server. See the [project configuration](#project-configuration) section below for how to configure a launch command for your project.

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

### Worktrunk Configuration

Configure [Worktrunk](https://worktrunk.dev) following their guide to start. You can add things like hooks to run after creating a workspace (`npm install`, etc). This project wraps their CLI with a TUI, so Worktrunk must be setup before using `wk`.

### `wk` Configuration

In `PROJECT_ROOT/.config/wk.yml` you can add custom commands which will appear as actions you can launch from the `wk` TUI:

**Fields**
 - open_workspace_cmd: the "launch workspace" command. If missing, launch option won't appear in TUI. Useful for tools like tmux/zellij.
 - restart_workspace_cmd: a command to restart a workspace (eg, killing a tmux session). If missing, restart option won't appear in TUI.
 - custom_commands: a set of custom commands you can invoke from the TUI, from the provided shortcut character. Eg: "t" runs tests on a worktree.

**Example `PROJECT_ROOT/.config/wk.yml`**
```yaml
open_workspace_cmd: tmux new-session ...
restart_workspace_cmd: tmux kill-session ... && tmux new-session ...

custom_commands:
  t:
    name: Test
    command: npm test
```
