"""Theme and styling for TUI."""


class ThemeColors:
    """Named color constants for programmatic use (outside CSS).

    Colors are inspired by the Dracula theme for excellent terminal readability.
    """

    ACCENT: str = "#50fa7b"  # Bright green - "New Worktree" row, highlights
    TEXT: str = "#f8f8f2"  # White/light - Primary text
    TEXT_DIM: str = "#6272a4"  # Gray - Timestamps, secondary info
    BACKGROUND: str = "#282a36"  # Dark - App background
    SELECTED: str = "#44475a"  # Muted purple - Highlighted row
    ERROR: str = "#ff5555"  # Red - Error notifications
    SUCCESS: str = "#50fa7b"  # Green - Success confirmations


APP_CSS = """
/* App-level */
Screen {
    background: $background;
    align: center middle;
}

/* Worktree list */
WorktreeList {
    width: 100%;
    height: 100%;
}

WorktreeList > ListItem {
    height: 1;
    padding: 0 2;
}

WorktreeList > ListItem:focus {
    background: $selected;
}

WorktreeList > ListItem:hover {
    background: $selected;
}

/* "New Worktree" row */
.new-worktree {
    color: $accent;
    text-style: bold;
}

/* Worktree item layout */
.worktree-row {
    layout: horizontal;
    height: 1;
}

.worktree-name {
    width: 1fr;
}

.worktree-time {
    color: $text-dim;
    text-align: right;
    width: auto;
}

/* Footer */
Footer {
    background: $background;
}

/* Input overlay */
.input-container {
    align: center middle;
}

Input {
    width: 40;
}
"""
