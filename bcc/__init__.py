"""Top-level package for baikalctl."""

from .app import app
from .client_cli import bcc
from .server_cli import baikalctl
from .version import __author__, __email__, __timestamp__, __version__

__all__ = ["app", "baikalctl", "bcc", "__version__", "__timestamp__", "__author__", "__email__"]
