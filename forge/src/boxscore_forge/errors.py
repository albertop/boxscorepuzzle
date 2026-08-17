"""The project's exception hierarchy.

Rooted at one class so a caller can catch what the forge raises without catching everything else
that might go wrong at the same time.
"""


class ForgeError(Exception):
    """Base class for every error the forge raises."""


class ContradictionError(ForgeError):
    """The values on a board cannot all be true at once.

    Raised while solving rather than returned, because there is nothing useful to do with a partial
    answer derived from givens that contradict each other. A puzzle that reaches this is discarded.
    """
