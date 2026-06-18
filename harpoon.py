import sublime
import sublime_plugin
import os

BOOKMARK_KEY = "harpoon_marks"


def get_marks(window):
    """Read the mark list from the window's project_data.

    Returns a list of dicts: {"path": str, "row": int, "col": int}
    or None if no project is open.
    """
    data = window.project_data()
    if data is None:
        return None  # no project open

    marks = data.get(BOOKMARK_KEY, [])

    # Backward-compat: upgrade old "list of path strings" format.
    upgraded = []
    changed = False
    for m in marks:
        if isinstance(m, str):
            upgraded.append({"path": m, "row": 0, "col": 0})
            changed = True
        else:
            upgraded.append(m)

    if changed:
        save_marks(window, upgraded)

    return upgraded


def save_marks(window, marks):
    data = window.project_data()
    if data is None:
        # No .sublime-project file loaded; create a minimal in-memory
        # project so data has somewhere to live for this window session.
        data = {}
    data[BOOKMARK_KEY] = marks
    window.set_project_data(data)


def require_project(window):
    if window.project_file_name() is None:
        sublime.error_message(
            "Harpoon: this window has no .sublime-project file.\n\n"
            "Use Project > Save Project As... first.\n\n"
            "Or Install AutoProject plugin."
        )
        return False
    return True


def mark_paths(marks):
    return [m["path"] for m in marks]


def find_mark(marks, file_name):
    for m in marks:
        if m["path"] == file_name:
            return m
    return None


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

        data = window.project_data()
        if data is None:
            return

        marks = data.get(BOOKMARK_KEY, [])
        # Skip the legacy-format upgrade dance here; if marks are still in
        # old string format they simply won't match and nothing updates.
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
            data[BOOKMARK_KEY] = marks
            window.set_project_data(data)

    def on_deactivated(self, view):
        self._update_position(view)

    def on_pre_close(self, view):
        self._update_position(view)


class HarpoonAddCommand(sublime_plugin.WindowCommand):
    """Add or remove the current file from this project's Harpoon list."""

    def run(self):
        if not require_project(self.window):
            return

        view = self.window.active_view()
        if not view:
            return

        file_name = view.file_name()
        if not file_name:
            sublime.status_message("Harpoon: save the file first")
            return

        marks = get_marks(self.window) or []
        existing = find_mark(marks, file_name)

        if existing is not None:
            marks.remove(existing)
            sublime.status_message("Harpoon: unmarked %s" % os.path.basename(file_name))
        else:
            row, col = cursor_position(view)
            marks.append({"path": file_name, "row": row, "col": col})
            sublime.status_message("Harpoon: marked %s" % os.path.basename(file_name))

        save_marks(self.window, marks)


class HarpoonListCommand(sublime_plugin.WindowCommand):
    """Show quick panel of this project's harpooned files."""

    def run(self):
        if not require_project(self.window):
            return

        marks = get_marks(self.window) or []

        valid = [m for m in marks if os.path.isfile(m["path"])]
        if valid != marks:
            save_marks(self.window, valid)
        marks = valid

        if not marks:
            sublime.status_message("Harpoon: no marks in this project")
            return

        items = [[os.path.basename(m["path"]), m["path"]] for m in marks]

        self.window.show_quick_panel(
            items,
            self.on_select,
            sublime.MONOSPACE_FONT,
        )
        self._marks = marks

    def on_select(self, index):
        if index == -1:
            return
        goto_mark(self.window, self._marks[index])


class HarpoonGotoCommand(sublime_plugin.WindowCommand):
    """Jump directly to mark N (1-indexed) in this project's list."""

    def run(self, index):
        if not require_project(self.window):
            return

        marks = get_marks(self.window) or []
        marks = [m for m in marks if os.path.isfile(m["path"])]

        if index < 1 or index > len(marks):
            sublime.status_message("Harpoon: no mark at slot %d" % index)
            return

        goto_mark(self.window, marks[index - 1])


class HarpoonNextCommand(sublime_plugin.WindowCommand):
    """Cycle to the next harpooned file in this project."""

    def run(self):
        self._cycle(1)

    def _cycle(self, direction):
        if not require_project(self.window):
            return

        marks = get_marks(self.window) or []
        marks = [m for m in marks if os.path.isfile(m["path"])]
        if not marks:
            sublime.status_message("Harpoon: no marks in this project")
            return

        view = self.window.active_view()
        current = view.file_name() if view else None
        paths = mark_paths(marks)

        if current in paths:
            idx = (paths.index(current) + direction) % len(marks)
        else:
            idx = 0

        goto_mark(self.window, marks[idx])


class HarpoonPrevCommand(HarpoonNextCommand):
    """Cycle to the previous harpooned file in this project."""

    def run(self):
        self._cycle(-1)


class HarpoonClearCommand(sublime_plugin.WindowCommand):
    """Clear all harpooned files for this project."""

    def run(self):
        if not require_project(self.window):
            return
        save_marks(self.window, [])
        sublime.status_message("Harpoon: cleared marks for this project")
