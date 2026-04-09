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
    WARNING: str = "#f1fa8c"  # Yellow - Warnings, ATTACH advice
    INFO: str = "#8be9fd"  # Cyan - Info, pending status


APP_CSS = """
/* Theme variables - Dracula-inspired */
$background: #282a36;
$accent: #50fa7b;
$text: #f8f8f2;
$text-dim: #6272a4;
$selected: #44475a;
$error: #ff5555;

/* App-level */
Screen {
    background: $background;
}

/* Worktree list */
WorktreeList {
    width: 100%;
    height: 1fr;
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

/* Row with status columns */
.worktree-row-text {
    width: 1fr;
}

/* Column header */
#column-header {
    color: $text-dim;
    text-style: bold underline;
    padding: 0 2;
    height: 1;
    width: 100%;
}

/* Filter indicator */
#filter-indicator {
    color: $accent;
    text-style: bold;
    padding: 0 2;
    height: 1;
    display: none;
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
