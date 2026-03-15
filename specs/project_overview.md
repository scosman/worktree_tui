# Project Overview: Worktrunk TUI

We have a project setup with worktunk: https://worktrunk.dev - see WT_README.md

We also have a custom "start.sh" script to launch a dev environment (multi-tab zellij, running the app).

## Project: Create a TUI

I want a nice easy to use TUI and CLI named `wk`

### main page (launch with no args)

A list of all worktrees (via `wt list`), you can naviate with keyboard.

 - First item in list is "New Workspace"
 - Rest of items are all the worktrees, sorted by created date
 - Second item is selected firt (not New Workspace, most recent worktree)
 
"New Worktree" prompts the user for a worktree name. Then creates a worktree and launches it's workspace. 

Selecting existing worktree
 - Launch Workspace: see below
 - Jump: change to wt directory
 - Delete: remove worktree (with confirmation)
 - Restart: retsarts the workspace with RESTART_WORKSPACE_CMD (with confirmation)

### Base Branch

creating a new worktree via "new" or TUI should branch off the corrent branch (wt defaults to main). This can be done with the --base option.

### "Launching" a worktree workspace

Launching just means changing directory to the worktree (or wt switch) then calling the open workspace command (see below)

### Config

Expect a config file in `.config/wk.yml` with

 - OPEN_WORKSPACE_CMD: the "launch workspace" command. If missing, launch is a no-op.
 - RESTART_WORKSPACE_CMD: the "launch workspace" command. If missing, launch is a no-op.

### CLI Commands

On top of interactive TUI, I want to be able to use CLI commands

#### `wk new FEATURE_NAME`

same as selecting New Worktree option and entering name

#### `wk FEATURE_NAME`

Same as launching a existing worktree

## Tech

Make a polished Python TUI. Nice UI. Color.

