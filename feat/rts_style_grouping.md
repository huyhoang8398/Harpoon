# Plan: RTS-style slot grouping

## Current state

`harpoon_add` appends the current file to a dense list `[{path, row, col}, ...]`.
A mark's slot = its position in the list. The user cannot choose which slot a file goes into.

## Goal

| Shortcut | Action |
|---|---|
| `ctrl+shift+N` | Assign current file to slot N |
| `ctrl+N` | Jump to slot N (unchanged) |

Rules:
- **Toggle**: `ctrl+shift+2` on a file already in slot 2 → slot 2 becomes empty.
- **Swap**: `ctrl+shift+2` on a file when slot 2 is taken by another file → old file is silently replaced.
- `harpoon_add` (auto-assign) is **kept**: finds the first empty slot or appends.

## Architecture decisions

### Data model: sparse list with `None`

```python
# Before
marks = [{"path": "a.py", "row": 0, "col": 0},
         {"path": "b.py", "row": 5, "col": 2}]

# After (slot 2 empty)
marks = [{"path": "a.py", "row": 0, "col": 0},
         None,
         {"path": "b.py", "row": 5, "col": 2}]
```

- `marks[i]` = slot `i+1` (preserves the 1-based convention of `harpoon_goto`).
- `None` = empty slot.
- JSON-serialisable (`null`).
- Backward compat: existing dense lists of dicts require no change — no `None` is injected.

### New command: `harpoon_add_to_slot`

```json
{ "keys": ["ctrl+shift+2"], "command": "harpoon_add_to_slot", "args": {"index": 2} }
```

Logic:
1. If `marks[index-1]` == current file → `marks[index-1] = None` (toggle).
2. If `marks[index-1]` is a different file → silent replacement (swap).
3. If `marks[index-1]` is `None` → direct assignment.
4. Extend the list if `index > len(marks)`.

### `harpoon_add` (auto)

New behavior with sparse list:
- If the file is already in any slot → set that slot to `None`, message "unmarked".
- Otherwise → use first `None` slot in the list, or append if no gap exists.

### `harpoon_list`

Shows **all** slots (including empty ones):
`["slot 1 — a.py", "slot 2 — (empty)", "slot 3 — b.py"]`
Selecting an empty slot → `status_message("Harpoon: slot N is empty")`, no navigation.

### `harpoon_goto`

- If `index < 1` or `index > len(marks)` → `status_message("Harpoon: no mark at slot N")`.
- If `marks[index-1]` is `None` → `status_message("Harpoon: slot N is empty")`.
- **Do not compact the list before indexing** (was a bug in the original code with sparse lists).
- Invalid file (deleted/moved): set slot to `None`, show `status_message`.

### `harpoon_next` / `harpoon_prev`

- Filter out `None` slots before cycling (do **not** compact the source list).
- If filtered list is empty → `status_message("Harpoon: no marks in this window")`.

### Pruning (invalid marks)

Replace removal with `None` assignment instead of `list.remove()`.
This preserves slot numbers of all other marks.

Affected locations:
- `HarpoonListCommand` — currently does `valid = [m for m in marks if isfile(m["path"])]`. Must become: set invalid entries to `None`, keep list structure.
- `HarpoonGotoCommand` — currently compacts before indexing. Must be removed entirely.
- `HarpoonNextCommand._cycle` — currently compacts before cycling. Must filter for navigation only, not mutate.

### `HarpoonTracker`

Already robust: the `isinstance(m, dict)` check in the loop implicitly skips `None` entries. No structural change needed — only protect the loop explicitly with `if m is None: continue`.

---

## `marks.py` scope (pure functions only)

Only functions with **no Sublime Text dependency** go into `marks.py`:

| Function | Pure? | Location |
|---|---|---|
| `find_mark(marks, file_name)` | ✅ | `marks.py` |
| `mark_paths(marks)` | ✅ | `marks.py` |
| `get_mark_at(marks, index)` | ✅ new | `marks.py` |
| `set_mark_at(marks, index, mark_or_none)` | ✅ new | `marks.py` |
| `find_mark_slot(marks, file_name)` | ✅ new | `marks.py` |
| `upgrade_marks(marks)` | ✅ extracted from `get_marks` | `marks.py` |
| `get_marks(window)` | ❌ ST API | `harpoon.py` |
| `save_marks(window, marks)` | ❌ ST API | `harpoon.py` |
| `cursor_position(view)` | ❌ ST API | `harpoon.py` |
| `goto_mark(window, mark)` | ❌ ST API | `harpoon.py` |

Final file structure:
```
Harpoon/
  marks.py        # pure list-manipulation logic, no ST dependency
  harpoon.py      # ST commands + wrappers around marks.py
  tests/
    test_marks.py
```

---

## Working rules

> These rules apply to **every step** without exception.

1. **Comment before modifying**: for every file touched, write the docblock + introductory comment *before* functional changes.
2. **Separate commit if significant**: if commenting requires substantial effort, commit comments alone (`docs(ID): add docblock to <file>`) before the functional commit.
3. **`*.sublime-*` files in sync**: any step adding/modifying/removing a command updates `Default.sublime-commands` and `Example.sublime-keymap` in the same commit. `Main.sublime-menu` only needs updating if a new menu entry is added (currently none planned).
4. **All comments and docs in English**: code comments, docstrings, status messages, README, CLAUDE.md, this plan.
5. **Commit identifier**: ask the user for the ticket/identifier before proposing any commit message.
6. **Explicit validation** required before moving to the next step.

---

## Step-by-step plan (strict TDD, one step at a time)

### ~~Step 1 — Test infrastructure + extract `marks.py`~~ ✅

Create `marks.py` with the **pure functions only** (see table above):
- Move `find_mark`, `mark_paths` from `harpoon.py`.
- Extract `upgrade_marks` from `get_marks` (the backward-compat logic, no ST dependency).
- `harpoon.py` calls `marks.py` functions; `get_marks`/`save_marks`/`cursor_position`/`goto_mark` stay in `harpoon.py`.

Create `tests/test_marks.py` covering existing behavior (regression tests).
Run `pytest tests/` — all tests must pass.
**Validation required before continuing.**

### ~~Step 2 — Sparse model (`None` in the list)~~ ✅

Add to `marks.py`:
- `get_mark_at(marks, index)` → returns the mark dict or `None`.
- `set_mark_at(marks, index, mark_or_none)` → extends list if necessary.
- `find_mark_slot(marks, file_name)` → returns 0-based index or `-1`.

Add tests: normal cases, list extension, `None` handling, backward compat.
Run `pytest tests/` — all tests must pass.
**Validation required.**

### ~~Step 3 — New command `HarpoonAddToSlotCommand`~~ ✅

Implement toggle + swap in `harpoon.py`.
Update `Default.sublime-commands` and `Example.sublime-keymap` (`ctrl+shift+1..5`).
Manual ST tests: toggle, swap, empty slot assignment.
**Validation required.**

### ~~Step 4 — Update `harpoon_add` (auto)~~ ✅

- Unmark: `set_mark_at(marks, slot, None)` instead of `marks.remove(...)`.
- Auto-mark: find first `None` or append.

Add unit tests.
**Validation required.**

### ~~Step 5 — Update `harpoon_list`~~ ✅

- Show all slots including empty ones.
- Selecting an empty slot → status message, no navigation.
- Pruning: set invalid entries to `None` instead of removing them.

Manual ST tests.
**Validation required.**

### ~~Step 6 — Update `harpoon_goto`, `harpoon_next`, `harpoon_prev`~~ ✅

`harpoon_goto`:
- Remove the compacting filter (`[m for m in marks if isfile]`).
- Handle `None` slot → status message.
- Handle deleted file → set slot to `None`, status message.

`harpoon_next` / `harpoon_prev`:
- Remove the compacting filter.
- Filter `None` for navigation only (do not mutate the list).
- Handle all-empty case.

Add unit tests.
**Validation required.**

### ~~Step 7 — Update `HarpoonTracker` + pruning consolidation~~ ✅

- Add explicit `if m is None: continue` guard in the tracker loop.
- Verify pruning behavior is consistent across all commands.

Add unit tests.
**Validation required.**

### ~~Step 8 — Docs~~ ✅

Update `README.md` to reflect new commands, data model, and file structure.
**Validation required.**

---

## Unchanged

- `harpoon_clear`: empties the entire list (no change).
- `goto_mark()`: file open + cursor repositioning logic (no change).
- Storage key `"harpoon_marks"` (no change — SSOT).
- `Main.sublime-menu`: points to `Example.sublime-keymap`, no new menu entry needed.