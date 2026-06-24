"""
marks.py — Pure list-manipulation helpers for Harpoon marks.

No Sublime Text dependency. All functions operate on plain Python
lists/dicts so they can be unit-tested without mocking the ST API.

Mark format  : {"path": str, "row": int, "col": int}
Sparse list  : marks[i] is None means slot i+1 is empty.
"""


def upgrade_marks(marks):
    """Upgrade old mark format (list of path strings) to list of dicts.

    Returns a (upgraded_list, changed) tuple.
    'changed' is True when at least one entry was converted.
    """
    upgraded = []
    changed = False
    for m in marks:
        if isinstance(m, str):
            upgraded.append({"path": m, "row": 0, "col": 0})
            changed = True
        else:
            upgraded.append(m)
    return upgraded, changed


def find_mark(marks, file_name):
    """Return the mark dict whose path matches file_name, or None."""
    for m in marks:
        if isinstance(m, dict) and m["path"] == file_name:
            return m
    return None


def mark_paths(marks):
    """Return the list of paths from a (possibly sparse) marks list."""
    return [m["path"] for m in marks if isinstance(m, dict)]


def get_mark_at(marks, index):
    """Return the mark dict at slot index (1-based), or None if empty/out of range."""
    i = index - 1
    if i < 0 or i >= len(marks):
        return None
    return marks[i]


def set_mark_at(marks, index, mark_or_none):
    """Set slot index (1-based) to mark_or_none, extending the list with None if needed.

    Mutates marks in place and returns it.
    """
    i = index - 1
    while len(marks) <= i:
        marks.append(None)
    marks[i] = mark_or_none
    return marks


def find_mark_slot(marks, file_name):
    """Return the 0-based index of the mark matching file_name, or -1 if not found."""
    for i, m in enumerate(marks):
        if isinstance(m, dict) and m["path"] == file_name:
            return i
    return -1


def find_free_slot(marks):
    """Return the 0-based index of the first None slot, or -1 if the list is full."""
    try:
        return marks.index(None)
    except ValueError:
        return -1
