"""Top-level package for bcc."""

from .app import app
from .cli import bcc
from .version import __author__, __email__, __timestamp__, __version__

__all__ = ["app", "bcc", "__version__", "__timestamp__", "__author__", "__email__"]
