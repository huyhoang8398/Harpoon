import os
import tempfile
import sublime
import sublime_plugin

BOOKMARK_KEY = "harpoon_marks"


def get_marks(window):
    """Read the mark list from the window's settings.

    Returns a list of dicts: {"path": str, "row": int, "col": int}
    """
    settings = window.settings()
    marks = settings.get(BOOKMARK_KEY)
    if not isinstance(marks, list):
        marks = []

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
    """Persist marks into the window's session settings without touching disk."""
    window.settings().set(BOOKMARK_KEY, marks)


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


def find_editor_view(window):
    for view in window.views():
        if view.settings().get("harpoon_editor"):
            return view
    return None


def parse_marks(view, old_marks):
    content = view.substr(sublime.Region(0, view.size()))
    old_index = {m["path"]: m for m in old_marks}
    new_marks = []
    seen = set()
    for line in content.splitlines():
        p = line.strip()
        if not p or p in seen:
            continue
        seen.add(p)
        new_marks.append(old_index.get(p, {"path": p, "row": 0, "col": 0}))
    return new_marks


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


class HarpoonEditorListener(sublime_plugin.EventListener):
    """Handles the editor view: commits on modification and on close"""

    def _is_editor(self, view):
        return bool(view.settings().get("harpoon_editor"))

    def _commit(self, view):
        window = view.window()
        if window is None:
            return
        save_marks(window, parse_marks(view, get_marks(window)))

    def on_modified(self, view):
        if not self._is_editor(view):
            return
        def _do():
            if view.settings().get("harpoon_editor"):
                self._commit(view)
        sublime.set_timeout(_do, 300)

    def on_pre_close(self, view):
        if not self._is_editor(view):
            return
        self._commit(view)

    def on_close(self, view):
        tmp = view.settings().get("harpoon_editor_tmp")
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


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
        existing = find_mark(marks, file_name)

        if existing is not None:
            marks.remove(existing)
            sublime.status_message(
                "Harpoon: unmarked %s" % os.path.basename(file_name)
            )
        else:
            row, col = cursor_position(view)
            marks.append({"path": file_name, "row": row, "col": col})
            sublime.status_message(
                "Harpoon: marked %s" % os.path.basename(file_name)
            )

        save_marks(self.window, marks)


class HarpoonListCommand(sublime_plugin.WindowCommand):
    """Show quick panel of this window's harpooned files."""

    def run(self):
        marks = get_marks(self.window)

        valid = [m for m in marks if os.path.isfile(m["path"])]
        if valid != marks:
            save_marks(self.window, valid)
        marks = valid

        if not marks:
            sublime.status_message("Harpoon: no marks in this window")
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


class HarpoonEditCommand(sublime_plugin.WindowCommand):
    """Open a temp file to edit the mark list, One path per line
    Changes commit to memory on every modification. save, close (:w/:wq on Neovintageous)saves silently
    """

    def run(self):
        existing = find_editor_view(self.window)
        if existing is not None:
            self.window.focus_view(existing)
            return

        content = "\n".join(m["path"] for m in get_marks(self.window))

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".harpoon", delete=False, encoding="utf-8"
        )
        tmp.write(content)
        tmp.close()

        view = self.window.open_file(tmp.name)
        view.set_name("Harpoon — Edit Marks")
        view.settings().set("harpoon_editor", True)
        view.settings().set("harpoon_editor_tmp", tmp.name)
        view.settings().set("word_wrap", False)


class HarpoonGotoCommand(sublime_plugin.WindowCommand):
    """Jump directly to mark N (1-indexed) in this window's list."""

    def run(self, index):
        marks = get_marks(self.window)
        marks = [m for m in marks if os.path.isfile(m["path"])]

        if index < 1 or index > len(marks):
            sublime.status_message("Harpoon: no mark at slot %d" % index)
            return

        goto_mark(self.window, marks[index - 1])


class HarpoonNextCommand(sublime_plugin.WindowCommand):
    """Cycle to the next harpooned file in this window."""

    def run(self):
        self._cycle(1)

    def _cycle(self, direction):
        marks = get_marks(self.window)
        marks = [m for m in marks if os.path.isfile(m["path"])]
        if not marks:
            sublime.status_message("Harpoon: no marks in this window")
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
    """Cycle to the previous harpooned file in this window."""

    def run(self):
        self._cycle(-1)


class HarpoonClearCommand(sublime_plugin.WindowCommand):
    """Clear all harpooned files for this window."""

    def run(self):
        save_marks(self.window, [])
        sublime.status_message("Harpoon: cleared marks for this window")