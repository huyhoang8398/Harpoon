import sublime
import sublime_plugin
import os

BOOKMARK_KEY = "harpoon_marks"


def get_marks(window):
    """Read the mark list from the window's project_data."""
    data = window.project_data()
    if data is None:
        return None  # no project open
    return data.get(BOOKMARK_KEY, [])


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

        if file_name in marks:
            marks.remove(file_name)
            sublime.status_message("Harpoon: unmarked %s" % os.path.basename(file_name))
        else:
            marks.append(file_name)
            sublime.status_message("Harpoon: marked %s" % os.path.basename(file_name))

        save_marks(self.window, marks)


class HarpoonListCommand(sublime_plugin.WindowCommand):
    """Show quick panel of this project's harpooned files."""

    def run(self):
        if not require_project(self.window):
            return

        marks = get_marks(self.window) or []

        valid = [m for m in marks if os.path.isfile(m)]
        if valid != marks:
            save_marks(self.window, valid)
        marks = valid

        if not marks:
            sublime.status_message("Harpoon: no marks in this project")
            return

        items = [[os.path.basename(p), p] for p in marks]

        self.window.show_quick_panel(
            items,
            self.on_select,
            sublime.MONOSPACE_FONT,
        )
        self._marks = marks

    def on_select(self, index):
        if index == -1:
            return
        self.window.open_file(self._marks[index])


class HarpoonGotoCommand(sublime_plugin.WindowCommand):
    """Jump directly to mark N (1-indexed) in this project's list."""

    def run(self, index):
        if not require_project(self.window):
            return

        marks = get_marks(self.window) or []
        marks = [m for m in marks if os.path.isfile(m)]

        if index < 1 or index > len(marks):
            sublime.status_message("Harpoon: no mark at slot %d" % index)
            return

        self.window.open_file(marks[index - 1])


class HarpoonNextCommand(sublime_plugin.WindowCommand):
    """Cycle to the next harpooned file in this project."""

    def run(self):
        self._cycle(1)

    def _cycle(self, direction):
        if not require_project(self.window):
            return

        marks = get_marks(self.window) or []
        marks = [m for m in marks if os.path.isfile(m)]
        if not marks:
            sublime.status_message("Harpoon: no marks in this project")
            return

        view = self.window.active_view()
        current = view.file_name() if view else None

        if current in marks:
            idx = (marks.index(current) + direction) % len(marks)
        else:
            idx = 0

        self.window.open_file(marks[idx])


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
