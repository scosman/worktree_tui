# Component: `tui/theme.py`

**Location**: `src/wk/tui/theme.py`

## Goal

Centralized styling for the TUI. Defines the color palette, CSS, and style constants used across all widgets. Ensures a polished, consistent look without scattering style definitions throughout the codebase.

## Public Interface

```python
APP_CSS: str
"""Textual CSS string for the entire application.

Loaded by WkApp via the CSS class variable or CSS_PATH.
Defines styles for:
- Overall app layout (background, padding)
- Header bar
- WorktreeList and its items
- Selected/highlighted row
- "New Worktree" row accent styling
- Input fields (new worktree name, confirmations)
- Footer bar with keybinding hints
"""

class ThemeColors:
    """Named color constants for programmatic use (outside CSS)."""
    ACCENT: str       # For "New Worktree" row, highlights
    TEXT: str          # Primary text
    TEXT_DIM: str      # Secondary text (timestamps, paths)
    BACKGROUND: str   # App background
    SELECTED: str     # Selected row background
    ERROR: str        # Error notifications
    SUCCESS: str      # Success notifications
```

## CSS Structure

The CSS is a single string constant (`APP_CSS`) that the `WkApp` loads. It uses Textual's CSS dialect (subset of CSS with Textual-specific selectors).

### Key Selectors

```css
/* App-level */
Screen { ... }

/* Header */
Header { ... }

/* Worktree list */
WorktreeList { ... }
WorktreeList > ListItem { ... }
WorktreeList > ListItem.--highlight { ... }

/* "New Worktree" row */
WorktreeList > .new-worktree { ... }

/* Worktree item layout */
.worktree-name { ... }
.worktree-time { ... }

/* Input overlay (new worktree name) */
.input-container { ... }
Input { ... }

/* Footer */
Footer { ... }
```

## Color Palette

A modern, terminal-friendly palette that works on both dark and light backgrounds (but optimized for dark):

| Role      | Color                         | Usage                              |
|-----------|-------------------------------|------------------------------------|
| Accent    | Bright green (`#50fa7b`)      | "New Worktree" row, call-to-action |
| Text      | White/light (`#f8f8f2`)       | Primary text                       |
| Text dim  | Gray (`#6272a4`)              | Timestamps, secondary info         |
| Background| Dark (`#282a36`)              | App background                     |
| Selected  | Muted purple (`#44475a`)      | Highlighted row                    |
| Error     | Red (`#ff5555`)               | Error messages                     |
| Success   | Green (`#50fa7b`)             | Success confirmations              |

*Note*: Exact colors will be tuned during implementation. These are starting points inspired by the Dracula theme, which has excellent terminal readability.

## Design Patterns

- **Single source of truth**: all visual styling lives here. Widgets reference CSS class names, not inline styles.
- **Constants module**: `ThemeColors` provides named constants for any programmatic styling that can't be done in CSS (e.g. Rich markup in notifications).
- **Separation from behavior**: this module contains zero logic — only declarations.

## Dependencies (internal)

None. Leaf module consumed by `tui/app.py` and `tui/worktree_list.py`.

## Dependencies (external)

None. Pure string constants.

## Testing Strategy

Theme is declarative — minimal testing needed, focused on validity rather than behavior.

### Test Cases

| # | Test Case | Method |
|---|-----------|--------|
| 1 | `APP_CSS` is valid Textual CSS | Integration: load CSS into a minimal Textual app, assert no parse errors |
| 2 | `ThemeColors` constants are valid color strings | Unit: assert each constant matches hex color pattern or named color |
| 3 | Visual regression (optional) | Snapshot: use Textual's SVG snapshot testing to capture the app's rendered output and compare against a baseline |
