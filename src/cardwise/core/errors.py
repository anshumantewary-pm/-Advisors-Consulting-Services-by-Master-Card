"""Exception hierarchy. The CLI catches ``CardwiseError`` and nothing else."""

from __future__ import annotations


class CardwiseError(Exception):
    """Base class for every error cardwise raises on purpose."""


class ValidationError(CardwiseError, ValueError):
    """An input value makes no sense for the calculation (e.g. a negative balance)."""


class UnknownNameError(CardwiseError, KeyError):
    """A lookup by name (segment, benchmark, industry) found nothing."""

    def __str__(self) -> str:
        # KeyError wraps its message in quotes; show it plainly instead.
        return str(self.args[0]) if self.args else "unknown name"
