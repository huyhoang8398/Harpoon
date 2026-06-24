# Harpoon

A Sublime Text plugin for marking files and jumping back to them instantly.

Marks are scoped **per window**, stored via `window.settings()` and persisted by Sublime's session manager — no `.sublime-project` file required.

![preview](./preview.png)

## Features

- Auto-assign a file to the first free slot with one hotkey (`harpoon_add`)
- Pin a file to a **specific slot** with `harpoon_add_to_slot` (toggle + swap)
- Jump to any slot directly by number (`harpoon_goto`)
- Browse all slots in a quick panel, including empty ones (`harpoon_list`)
- Cycle forward/backward through marked files (`harpoon_next` / `harpoon_prev`)
- Dead marks (deleted or moved files) are replaced with empty slots automatically
- Marks persist across restarts; each window keeps its own independent list

## Installation

1. Open `Preferences > Browse Packages...` in Sublime Text.
2. Create a new folder called `Harpoon`.
3. Copy `harpoon.py` and `marks.py` into that folder.
4. Add the key bindings below via `Preferences > Key Bindings`.

## Commands

| Command               | Description |
|-----------------------|-------------|
| `harpoon_add`         | Auto-assign current file to the first free slot; toggle unmark if already marked |
| `harpoon_add_to_slot` | Assign current file to a specific slot (`index` arg, 1-based). Toggle if same file, swap if different file |
| `harpoon_list`        | Show a quick panel of all slots (empty slots visible but not navigable) |
| `harpoon_goto`        | Jump to a specific slot (`index` arg, 1-based) |
| `harpoon_next`        | Cycle to the next marked file |
| `harpoon_prev`        | Cycle to the previous marked file |
| `harpoon_clear`       | Clear all marks for the current window |

## Suggested key bindings

Add to your `Default.sublime-keymap` (`Preferences > Key Bindings`):

```json
[
    { "keys": ["ctrl+alt+a"], "command": "harpoon_add" },
    { "keys": ["ctrl+alt+e"], "command": "harpoon_list" },
    { "keys": ["ctrl+alt+]"], "command": "harpoon_next" },
    { "keys": ["ctrl+alt+["], "command": "harpoon_prev" },
    { "keys": ["ctrl+alt+d"], "command": "harpoon_clear" },

    { "keys": ["ctrl+alt+1"], "command": "harpoon_add_to_slot", "args": {"index": 1} },
    { "keys": ["ctrl+alt+2"], "command": "harpoon_add_to_slot", "args": {"index": 2} },
    { "keys": ["ctrl+alt+3"], "command": "harpoon_add_to_slot", "args": {"index": 3} },
    { "keys": ["ctrl+alt+4"], "command": "harpoon_add_to_slot", "args": {"index": 4} },
    { "keys": ["ctrl+alt+5"], "command": "harpoon_add_to_slot", "args": {"index": 5} },

    { "keys": ["ctrl+1"], "command": "harpoon_goto", "args": {"index": 1} },
    { "keys": ["ctrl+2"], "command": "harpoon_goto", "args": {"index": 2} },
    { "keys": ["ctrl+3"], "command": "harpoon_goto", "args": {"index": 3} },
    { "keys": ["ctrl+4"], "command": "harpoon_goto", "args": {"index": 4} },
    { "keys": ["ctrl+5"], "command": "harpoon_goto", "args": {"index": 5} }
]
```

`harpoon_goto` and `harpoon_add_to_slot` accept any `index` — add more bindings for slots 6, 7, etc. if needed.

## Usage

1. Open a file you want to keep close at hand.
2. Press `ctrl+alt+a` to mark it (auto-assign). Press it again to unmark.
   — *or* — Press `ctrl+alt+1` to pin it to slot 1 specifically.
3. Mark more files. Use `ctrl+1`–`ctrl+5` to jump straight to a slot, `ctrl+alt+]` / `ctrl+alt+[` to cycle, or `ctrl+alt+e` to browse all slots in a quick panel.

### Slot assignment rules (`harpoon_add_to_slot`)

| Situation | Result |
|---|---|
| Slot is empty | File is assigned to that slot |
| Slot holds the **same** file | Slot is cleared (toggle) |
| Slot holds a **different** file | Old file is silently replaced (swap) |

### How marks are stored

Marks live under a `"harpoon_marks"` key in `window.settings()`. Sublime's session manager persists this automatically to your `.sublime-workspace` file (or global session cache for ad-hoc windows). No disk writes, no sidebar noise, no `.sublime-project` required.

Marks are stored as a **sparse list**: each index maps to a slot number (`marks[0]` = slot 1, `marks[1]` = slot 2, …). An empty slot is stored as `null` in JSON. This preserves slot numbers when a file is unmarked — other files stay in their slots.

Multiple windows running side-by-side maintain completely independent mark lists.

## Notes

- Marks require the file to be saved (have a path on disk); unsaved buffers cannot be marked.
- Marks are stored as absolute file paths. If a file is deleted or moved, its slot becomes empty automatically the next time you navigate or open the list.
