import harpoon


class FakeSettings:
    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def erase(self, key):
        self._data.pop(key, None)


class FakeWindow:
    def __init__(self):
        self._settings = FakeSettings()

    def settings(self):
        return self._settings

    def views(self):
        return []

    def active_view(self):
        return None


class FakeView:
    def __init__(self, content=""):
        self.content = content

    def size(self):
        return len(self.content)

    def substr(self, region):
        return self.content[region.a : region.b]


def test_find_mark_found():
    marks = [{"path": "/a", "row": 0, "col": 0}, {"path": "/b", "row": 1, "col": 2}]
    assert harpoon.find_mark(marks, "/b") == marks[1]


def test_find_mark_missing():
    assert harpoon.find_mark([], "/nope") is None


def test_mark_paths():
    assert harpoon.mark_paths([{"path": "/a"}, {"path": "/b"}]) == ["/a", "/b"]


def test_get_marks_defaults_to_empty_list():
    assert harpoon.get_marks(FakeWindow()) == []


def test_save_and_get_roundtrip():
    window = FakeWindow()
    marks = [{"path": "/a", "row": 1, "col": 2}]
    harpoon.save_marks(window, marks)
    assert harpoon.get_marks(window) == marks


def test_backward_compat_upgrades_string_list():
    window = FakeWindow()
    window.settings().set(harpoon.BOOKMARK_KEY, ["/legacy"])
    marks = harpoon.get_marks(window)
    assert marks == [{"path": "/legacy", "row": 0, "col": 0}]
    # upgrade must be persisted back, not just returned
    assert window.settings().get(harpoon.BOOKMARK_KEY) == marks


def test_parse_marks_preserves_known_positions():
    view = FakeView("/a\n/b")
    old_marks = [{"path": "/a", "row": 5, "col": 3}]
    new_marks = harpoon.parse_marks(view, old_marks)
    assert new_marks == [
        {"path": "/a", "row": 5, "col": 3},
        {"path": "/b", "row": 0, "col": 0},
    ]


def test_parse_marks_dedupes_and_skips_blanks():
    view = FakeView("/a\n\n/a\n  \n/b")
    new_marks = harpoon.parse_marks(view, [])
    assert harpoon.mark_paths(new_marks) == ["/a", "/b"]
