"""
tests/test_marks.py — Unit tests for marks.py pure functions.

Covers: upgrade_marks, find_mark, mark_paths.
These tests must pass with a plain 'pytest tests/' invocation —
no Sublime Text installation required.
"""
import sys
import os

# Allow importing marks.py from the project root without installation.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from marks import find_mark, mark_paths, upgrade_marks, get_mark_at, set_mark_at, find_mark_slot, find_free_slot


# ---------------------------------------------------------------------------
# upgrade_marks
# ---------------------------------------------------------------------------

def test_upgrade_marks_noop_on_dicts():
    marks = [{"path": "a.py", "row": 0, "col": 0}]
    result, changed = upgrade_marks(marks)
    assert result == marks
    assert changed is False


def test_upgrade_marks_converts_strings():
    marks = ["a.py", "b.py"]
    result, changed = upgrade_marks(marks)
    assert result == [
        {"path": "a.py", "row": 0, "col": 0},
        {"path": "b.py", "row": 0, "col": 0},
    ]
    assert changed is True


def test_upgrade_marks_mixed():
    marks = ["a.py", {"path": "b.py", "row": 1, "col": 2}]
    result, changed = upgrade_marks(marks)
    assert result[0] == {"path": "a.py", "row": 0, "col": 0}
    assert result[1] == {"path": "b.py", "row": 1, "col": 2}
    assert changed is True


def test_upgrade_marks_empty():
    result, changed = upgrade_marks([])
    assert result == []
    assert changed is False


def test_upgrade_marks_preserves_none_entries():
    # None (empty slot) must not be converted — it is not a legacy string.
    marks = [None, {"path": "a.py", "row": 0, "col": 0}]
    result, changed = upgrade_marks(marks)
    assert result == marks
    assert changed is False


# ---------------------------------------------------------------------------
# find_mark
# ---------------------------------------------------------------------------

def test_find_mark_found():
    marks = [{"path": "a.py", "row": 0, "col": 0}]
    assert find_mark(marks, "a.py") == marks[0]


def test_find_mark_not_found():
    marks = [{"path": "a.py", "row": 0, "col": 0}]
    assert find_mark(marks, "b.py") is None


def test_find_mark_empty_list():
    assert find_mark([], "a.py") is None


def test_find_mark_skips_none_entries():
    marks = [None, {"path": "a.py", "row": 0, "col": 0}]
    assert find_mark(marks, "a.py") == marks[1]


def test_find_mark_returns_first_match():
    # Duplicate paths should not exist in practice, but the function
    # must return the first one it finds.
    m1 = {"path": "a.py", "row": 0, "col": 0}
    m2 = {"path": "a.py", "row": 5, "col": 0}
    assert find_mark([m1, m2], "a.py") is m1


# ---------------------------------------------------------------------------
# mark_paths
# ---------------------------------------------------------------------------

def test_mark_paths_basic():
    marks = [
        {"path": "a.py", "row": 0, "col": 0},
        {"path": "b.py", "row": 1, "col": 2},
    ]
    assert mark_paths(marks) == ["a.py", "b.py"]


def test_mark_paths_empty():
    assert mark_paths([]) == []


def test_mark_paths_skips_none_entries():
    marks = [None, {"path": "a.py", "row": 0, "col": 0}, None]
    assert mark_paths(marks) == ["a.py"]


# ---------------------------------------------------------------------------
# get_mark_at  (1-based index)
# ---------------------------------------------------------------------------


def test_get_mark_at_returns_mark():
    m = {"path": "a.py", "row": 0, "col": 0}
    assert get_mark_at([m], 1) is m


def test_get_mark_at_empty_slot():
    assert get_mark_at([None], 1) is None


def test_get_mark_at_out_of_range():
    assert get_mark_at([], 1) is None
    assert get_mark_at([{"path": "a.py", "row": 0, "col": 0}], 5) is None


def test_get_mark_at_slot_2():
    m1 = {"path": "a.py", "row": 0, "col": 0}
    m2 = {"path": "b.py", "row": 1, "col": 0}
    assert get_mark_at([m1, m2], 2) is m2


# ---------------------------------------------------------------------------
# set_mark_at  (1-based index, mutates in place)
# ---------------------------------------------------------------------------


def test_set_mark_at_replaces_existing():
    m1 = {"path": "a.py", "row": 0, "col": 0}
    m2 = {"path": "b.py", "row": 0, "col": 0}
    marks = [m1]
    set_mark_at(marks, 1, m2)
    assert marks[0] is m2


def test_set_mark_at_sets_to_none():
    m = {"path": "a.py", "row": 0, "col": 0}
    marks = [m]
    set_mark_at(marks, 1, None)
    assert marks[0] is None


def test_set_mark_at_extends_list():
    marks = []
    m = {"path": "a.py", "row": 0, "col": 0}
    set_mark_at(marks, 3, m)
    assert len(marks) == 3
    assert marks[0] is None
    assert marks[1] is None
    assert marks[2] is m


def test_set_mark_at_returns_list():
    marks = []
    result = set_mark_at(marks, 1, None)
    assert result is marks


# ---------------------------------------------------------------------------
# find_mark_slot  (returns 0-based index or -1)
# ---------------------------------------------------------------------------


def test_find_mark_slot_found():
    m = {"path": "a.py", "row": 0, "col": 0}
    assert find_mark_slot([m], "a.py") == 0


def test_find_mark_slot_not_found():
    assert find_mark_slot([], "a.py") == -1
    m = {"path": "b.py", "row": 0, "col": 0}
    assert find_mark_slot([m], "a.py") == -1


def test_find_mark_slot_skips_none():
    m = {"path": "a.py", "row": 0, "col": 0}
    assert find_mark_slot([None, m], "a.py") == 1


def test_find_mark_slot_returns_correct_index():
    m1 = {"path": "a.py", "row": 0, "col": 0}
    m2 = {"path": "b.py", "row": 0, "col": 0}
    assert find_mark_slot([m1, m2], "b.py") == 1


# ---------------------------------------------------------------------------
# find_free_slot  (returns 0-based index of first None, or -1)
# ---------------------------------------------------------------------------


def test_find_free_slot_empty_list():
    assert find_free_slot([]) == -1


def test_find_free_slot_no_none():
    marks = [{"path": "a.py", "row": 0, "col": 0}]
    assert find_free_slot(marks) == -1


def test_find_free_slot_first_slot_free():
    assert find_free_slot([None]) == 0


def test_find_free_slot_middle_slot_free():
    m = {"path": "a.py", "row": 0, "col": 0}
    assert find_free_slot([m, None, m]) == 1


def test_find_free_slot_returns_first_free():
    m = {"path": "a.py", "row": 0, "col": 0}
    assert find_free_slot([None, None, m]) == 0
