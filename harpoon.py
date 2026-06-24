"""
harpoon.py — Sublime Text commands for the Harpoon plugin.

Thin ST wrapper around the pure list logic in marks.py.
All functions that depend on the Sublime API (window, view, sublime)
live here; everything else lives in marks.py and is unit-tested there.

Storage key: window.settings()["harpoon_marks"]
Mark format : {"path": str, "row": int, "col": int}
"""
import os
import sublime
import sublime_plugin

try:
    # Relative import when loaded by Sublime Text (module name: Harpoon.harpoon).
    from .marks import find_mark, mark_paths, upgrade_marks, get_mark_at, set_mark_at, find_mark_slot, find_free_slot
except ImportError:
    # Absolute import fallback for the pytest environment.
    from marks import find_mark, mark_paths, upgrade_marks, get_mark_at, set_mark_at, find_mark_slot, find_free_slot

BOOKMARK_KEY = "harpoon_marks"


def get_marks(window):
    """Read and return the mark list from the window's session settings.

    Automatically upgrades the legacy format (list of path strings) to
    the current format (list of dicts). Returns a list of dicts.
    """
    settings = window.settings()
    marks = settings.get(BOOKMARK_KEY)
    if not isinstance(marks, list):
        marks = []

    marks, changed = upgrade_marks(marks)
    if changed:
        save_marks(window, marks)

    return marks


def save_marks(window, marks):
    """Persist marks into the window's session settings without touching disk."""
    window.settings().set(BOOKMARK_KEY, marks)


def cursor_position(view):
    """Return (row, col) of the primary cursor in view."""
    sel = view.sel()
    if not sel:
        return (0, 0)
    pt = sel[0].b
    row, col = view.rowcol(pt)
    return (row, col)


def goto_mark(window, mark):
    """Open the file for mark and move the cursor/viewport to its saved position."""
    view = window.open_file(mark["path"])
    row = mark.get("row", 0)
    col = mark.get("col", 0)

    def _apply():
        if view.is_loading():
            sublime.set_timeout(_apply, 10)
            return
        pt = view.text_point(row, col)
        view.sel().clear()
        view.sel().add(sublime.Region(pt, pt))
        view.show_at_center(pt)

    _apply()


class HarpoonTracker(sublime_plugin.EventListener):
    """Keeps each mark's saved row/col up to date as files are used."""

    def _update_position(self, view):
        file_name = view.file_name()
        if not file_name:
            return

        window = view.window()
        if window is None:
            return

        settings = window.settings()
        marks = settings.get(BOOKMARK_KEY)
        if not isinstance(marks, list):
            return

        changed = False
        for m in marks:
            if isinstance(m, dict) and m.get("path") == file_name:
                row, col = cursor_position(view)
                if m.get("row") != row or m.get("col") != col:
                    m["row"] = row
                    m["col"] = col
                    changed = True
                break

        if changed:
            settings.set(BOOKMARK_KEY, marks)

    def on_deactivated(self, view):
        self._update_position(view)

    def on_pre_close(self, view):
        self._update_position(view)


class HarpoonAddToSlotCommand(sublime_plugin.WindowCommand):
    """Assign the current file to a specific slot (1-based index).

    Toggle  — pressing the same shortcut on a file already in that slot
              clears the slot.
    Swap    — if the slot is occupied by a different file, that file is
              silently replaced.
    """

    def run(self, index):
        view = self.window.active_view()
        if not view:
            return

        file_name = view.file_name()
        if not file_name:
            sublime.status_message("Harpoon: save the file first")
            return

        marks = get_marks(self.window)
        existing = get_mark_at(marks, index)

        if existing is not None and existing["path"] == file_name:
            set_mark_at(marks, index, None)
            sublime.status_message(
                "Harpoon: unmarked %s (slot %d)" % (os.path.basename(file_name), index)
            )
        else:
            row, col = cursor_position(view)
            set_mark_at(marks, index, {"path": file_name, "row": row, "col": col})
            sublime.status_message(
                "Harpoon: marked %s → slot %d" % (os.path.basename(file_name), index)
            )

        save_marks(self.window, marks)


class HarpoonAddCommand(sublime_plugin.WindowCommand):
    """Add or remove the current file from this window's Harpoon list."""

    def run(self):
        view = self.window.active_view()
        if not view:
            return

        file_name = view.file_name()
        if not file_name:
            sublime.status_message("Harpoon: save the file first")
            return

        marks = get_marks(self.window)
        slot_index = find_mark_slot(marks, file_name)  # 0-based, or -1

        if slot_index != -1:
            set_mark_at(marks, slot_index + 1, None)
            sublime.status_message(
                "Harpoon: unmarked %s" % os.path.basename(file_name)
            )
        else:
            row, col = cursor_position(view)
            mark = {"path": file_name, "row": row, "col": col}
            free = find_free_slot(marks)
            if free != -1:
                set_mark_at(marks, free + 1, mark)
            else:
                marks.append(mark)
            sublime.status_message(
                "Harpoon: marked %s" % os.path.basename(file_name)
            )

        save_marks(self.window, marks)


class HarpoonListCommand(sublime_plugin.WindowCommand):
    """Show all slots in a quick panel; empty slots are visible but not navigable."""

    def run(self):
        marks = get_marks(self.window)

        # Prune deleted/moved files in place to preserve slot numbers.
        changed = False
        for i, m in enumerate(marks):
            if m is not None and not os.path.isfile(m["path"]):
                marks[i] = None
                changed = True
        if changed:
            save_marks(self.window, marks)

        if not any(m is not None for m in marks):
            sublime.status_message("Harpoon: no marks in this window")
            return

        items = []
        for i, m in enumerate(marks):
            slot = i + 1
            if m is None:
                items.append(["slot %d — (empty)" % slot, ""])
            else:
                items.append(["slot %d — %s" % (slot, os.path.basename(m["path"])), m["path"]])

        self.window.show_quick_panel(items, self.on_select, sublime.MONOSPACE_FONT)
        self._marks = marks

    def on_select(self, index):
        if index == -1:
            return
        mark = self._marks[index]
        if mark is None:
            sublime.status_message("Harpoon: slot %d is empty" % (index + 1))
            return
        goto_mark(self.window, mark)


class HarpoonGotoCommand(sublime_plugin.WindowCommand):
    """Jump directly to slot N (1-based) without compacting the sparse list."""

    def run(self, index):
        marks = get_marks(self.window)
        mark = get_mark_at(marks, index)

        if mark is None:
            sublime.status_message("Harpoon: slot %d is empty" % index)
            return

        if not os.path.isfile(mark["path"]):
            set_mark_at(marks, index, None)
            save_marks(self.window, marks)
            sublime.status_message("Harpoon: slot %d — file not found" % index)
            return

        goto_mark(self.window, mark)


class HarpoonNextCommand(sublime_plugin.WindowCommand):
    """Cycle to the next harpooned file in this window."""

    def run(self):
        self._cycle(1)

    def _cycle(self, direction):
        marks = get_marks(self.window)
        # Build a navigation-only list — never mutate the sparse source list.
        navigable = [m for m in marks if m is not None and os.path.isfile(m["path"])]
        if not navigable:
            sublime.status_message("Harpoon: no marks in this window")
            return

        view = self.window.active_view()
        current = view.file_name() if view else None
        paths = mark_paths(navigable)

        if current in paths:
            idx = (paths.index(current) + direction) % len(navigable)
        else:
            idx = 0

        goto_mark(self.window, navigable[idx])


class HarpoonPrevCommand(HarpoonNextCommand):
    """Cycle to the previous harpooned file in this window."""

    def run(self):
        self._cycle(-1)


class HarpoonClearCommand(sublime_plugin.WindowCommand):
    """Clear all harpooned files for this window."""

    def run(self):
        save_marks(self.window, [])
        sublime.status_message("Harpoon: cleared marks for this window")
