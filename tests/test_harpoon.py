import os
import tempfile
import unittest

import sublime
from unittesting import DeferrableTestCase

import harpoon


def _make_temp_file(content=""):
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    with open(path, "w") as f:
        f.write(content)
    return path


class TestMarkStorage(unittest.TestCase):
    def setUp(self):
        self.window = sublime.active_window()
        self._orig = self.window.settings().get(harpoon.BOOKMARK_KEY)
        self.window.settings().erase(harpoon.BOOKMARK_KEY)

    def tearDown(self):
        if self._orig is None:
            self.window.settings().erase(harpoon.BOOKMARK_KEY)
        else:
            self.window.settings().set(harpoon.BOOKMARK_KEY, self._orig)

    def test_save_and_get_roundtrip(self):
        marks = [{"path": "/a", "row": 1, "col": 2}]
        harpoon.save_marks(self.window, marks)
        self.assertEqual(harpoon.get_marks(self.window), marks)


class TestHarpoonAddCommand(DeferrableTestCase):
    def setUp(self):
        self.window = sublime.active_window()
        self.path = _make_temp_file("hello\n")
        harpoon.save_marks(self.window, [])

    def tearDown(self):
        harpoon.save_marks(self.window, [])
        for view in self.window.views():
            if view.file_name() == self.path:
                view.close()
        os.remove(self.path)

    def test_add_then_remove_toggles(self):
        view = self.window.open_file(self.path)
        yield lambda: not view.is_loading()

        self.window.focus_view(view)
        self.window.run_command("harpoon_add")
        marks = harpoon.get_marks(self.window)
        self.assertEqual(len(marks), 1)
        self.assertEqual(marks[0]["path"], self.path)

        self.window.run_command("harpoon_add")
        self.assertEqual(harpoon.get_marks(self.window), [])
        view.close()


class TestHarpoonGotoCommand(DeferrableTestCase):
    def setUp(self):
        self.window = sublime.active_window()
        self.paths = [_make_temp_file(), _make_temp_file()]
        harpoon.save_marks(
            self.window, [{"path": p, "row": 0, "col": 0} for p in self.paths]
        )

    def tearDown(self):
        harpoon.save_marks(self.window, [])
        for p in self.paths:
            for view in self.window.views():
                if view.file_name() == p:
                    view.close()
            os.remove(p)

    def test_goto_out_of_range_is_noop(self):
        self.window.run_command("harpoon_goto", {"index": 99})  # must not raise

    def test_goto_opens_correct_file(self):
        self.window.run_command("harpoon_goto", {"index": 2})
        yield 50
        view = self.window.active_view()
        self.assertEqual(view.file_name(), self.paths[1])
        view.close()


class TestHarpoonClearCommand(unittest.TestCase):
    def test_clear_empties_marks(self):
        window = sublime.active_window()
        harpoon.save_marks(window, [{"path": "/a", "row": 0, "col": 0}])
        window.run_command("harpoon_clear")
        self.assertEqual(harpoon.get_marks(window), [])
