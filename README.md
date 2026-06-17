# Harpoon

A Sublime Text plugin for marking files and jumping back to them instantly.

Marks are scoped **per project**, stored inside your `.sublime-project` file, so each project keeps its own independent list.

![preview](./preview.png)

## Features

- Mark/unmark the current file with one hotkey
- Jump to any mark directly by slot number (1, 2, 3, 4...)
- Browse all marks in a quick panel
- Cycle forward/backward through marks
- Marks persist across restarts (saved in the `.sublime-project` file)
- Dead marks (deleted or moved files) are pruned automatically

## Installation

1. Open `Preferences > Browse Packages...` in Sublime Text.
2. Create a new folder called `Harpoon`.
3. Copy `Harpoon.py` into that folder.
4. Add the key bindings below via `Preferences > Key Bindings`.

## Requirements

Your window must have a saved `.sublime-project` file (`Project > Save Project As...`). Harpoon stores marks inside the project file itself, so without one there's nowhere durable to save them — commands will show an error pointing this out.
Easiest way is to install [AutoProject Plugin](https://packages.sublimetext.io/packages/AutoProjects) that will automatically create `.sublime-project`

## Commands

| Command            | Description                                      |
|---------------------|---------------------------------------------------|
| `harpoon_add`       | Mark the current file, or unmark it if already marked |
| `harpoon_list`      | Show a quick panel of all marks; select to open   |
| `harpoon_goto`      | Jump to a specific mark by slot (`index` arg, 1-indexed) |
| `harpoon_next`      | Cycle to the next mark                             |
| `harpoon_prev`      | Cycle to the previous mark                         |
| `harpoon_clear`     | Clear all marks for the current project            |

## Suggested key bindings

Add to your `Default.sublime-keymap` (`Preferences > Key Bindings`):

```json
[
    { "keys": ["ctrl+alt+a"], "command": "harpoon_add" },
    { "keys": ["ctrl+alt+e"], "command": "harpoon_list" },
    { "keys": ["ctrl+alt+]"], "command": "harpoon_next" },
    { "keys": ["ctrl+alt+["], "command": "harpoon_prev" },

    { "keys": ["ctrl+1"], "command": "harpoon_goto", "args": {"index": 1} },
    { "keys": ["ctrl+2"], "command": "harpoon_goto", "args": {"index": 2} },
    { "keys": ["ctrl+3"], "command": "harpoon_goto", "args": {"index": 3} },
    { "keys": ["ctrl+4"], "command": "harpoon_goto", "args": {"index": 4} }
]
```

Adjust freely — these are just suggestions, not hardcoded defaults. `harpoon_goto` accepts any `index`, so you aren't limited to four slots; add more bindings for `index: 5`, `6`, etc. if you want.

## Usage

1. Open a file you want to keep close at hand.
2. Press your `harpoon_add` key (e.g. `ctrl+alt+a`) to mark it. Press it again on the same file to unmark it.
3. Switch to another file, mark it too. Repeat as needed.
4. Use `ctrl+1`–`ctrl+4` (or your bound keys) to jump straight to a marked file by slot, `harpoon_next`/`harpoon_prev` to cycle through the list in order, or `harpoon_list` to see all marks in a quick panel and pick one.

## How it works

Marks are stored under a `harpoon_marks` key inside your project's data, accessed via Sublime's `project_data()` / `set_project_data()` API. Because that data lives in the `.sublime-project` file, it's automatically saved to disk and reloaded the next time you open the project, no separate settings file or database involved.

This also means:

- Different projects never share marks.
- Multiple windows with different projects open keep independent lists.
- If you close a window without ever saving a `.sublime-project` file for it, marks made during that session won't persist (see Requirements above).

## Notes

- Marks are stored as absolute file paths. Moving or renaming a project on disk won't break existing marks as long as the paths themselves remain valid; if a file is deleted or moved, its mark is silently dropped the next time you open the list or cycle through marks.
- `harpoon_add` requires the file to be saved (have a path on disk); it won't mark unsaved buffers.