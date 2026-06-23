import os
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
    """Persist marks into the window's session settings."""
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
            sublime.status_message("Harpoon: unmarked %s" % os.path.basename(file_name))
        else:
            row, col = cursor_position(view)
            marks.append({"path": file_name, "row": row, "col": col})
            sublime.status_message("Harpoon: marked %s" % os.path.basename(file_name))

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


class HarpoonSearchCommand(sublime_plugin.WindowCommand):
    """Search for text patterns exclusively inside your harpooned files.

    Outputs to a persistent buffer using your custom layout regex configurations.
    """

    def run(self):
        marks = get_marks(self.window)
        valid_marks = [m for m in marks if os.path.isfile(m["path"])]

        if not valid_marks:
            sublime.status_message("Harpoon: No files marked to search within")
            return

        self._valid_marks = valid_marks
        self.window.show_input_panel(
            "Search Harpoon Files:", "", self.on_done, None, None
        )

    def on_done(self, text):
        if not text:
            return

        occurrences = {}
        match_count = 0

        # Scan marked files
        for m in self._valid_marks:
            path = m["path"]
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f):
                        if text.lower() in line.lower():
                            if path not in occurrences:
                                occurrences[path] = []
                            occurrences[path].append((i + 1, line.rstrip()))
                            match_count += 1
            except Exception as e:
                print(f"Harpoon: Could not read {path}: {e}")

        if match_count == 0:
            sublime.status_message(f"Harpoon: No matches found for '{text}'")
            return

        # Create a dedicated results buffer
        view = self.window.new_file()
        view.set_name(f"Harpoon Search: {text}")
        view.set_scratch(True)  # Don't prompt to save on close

        # Apply your exact requested regex rules and syntax targets
        try:
            view.assign_syntax("Packages/Default/Find Results.hidden-tmLanguage")
        except Exception:
            try:
                view.assign_syntax("Packages/Default/Find Results.sublime-syntax")
            except Exception:
                try:
                    view.set_syntax_file(
                        "Packages/Default/Find Results.hidden-tmLanguage"
                    )
                except Exception:
                    pass

        view.settings().set("result_file_regex", r"^([^ \t].*):$")
        view.settings().set("result_line_regex", r"^ +([0-9]+):")

        # Build the output text matching the regex spacing requirements
        output = [f"Harpoon Search Results for '{text}' — {match_count} matches\n"]
        for path, lines in occurrences.items():
            # File lines must start flush against the margin (no spaces/tabs)
            output.append(f"\n{path}:")
            for line_num, line_text in lines:
                # Match lines must be prefixed with spaces to satisfy the regex
                output.append(f"  {line_num}: {line_text}")

        # Populate the view safely
        view.run_command("append", {"characters": "\n".join(output) + "\n"})
        self.window.focus_view(view)


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
