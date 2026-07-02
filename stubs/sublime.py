MONOSPACE_FONT = 1


class Region:
	__slots__ = ("a", "b")

	def __init__(self, a, b=None) -> None:
		self.a = a	
		self.b = a if b is None else b

	def __eq__(self, other):
		return isinstance(other, Region) and (self.a, self.b) == (other.a, other.b)

	def __repr__(self):
		return f"Region({self.a:!r} ,{self.b:!r})"


def set_timeout(callback, delay=0):
	callback()

def status_message(message):
	pass
