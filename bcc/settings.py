# settings

import socket
from pathlib import Path

from starlette.config import Config

config = Config()

ADDRESS = config("BAIKALCTL_ADDRESS", cast=str, default="0.0.0.0")
PORT = config("BAIKALCTL_PORT", cast=int, default=8000)

URL = config(
    "BAIKALCTL_URL", cast=str, default="http://caldav." + ".".join(socket.getfqdn().split(".")[1:]) + "/baikal"
)
CERT = config("BAIKALCTL_CERT", cast=str, default=str(Path.home() / "certs" / "client.pem"))
KEY = config("BAIKALCTL_KEY", cast=str, default=str(Path.home() / "certs" / "client.key"))
API_KEY = config("BAIKALCTL_API_KEY", cast=str, default="SET_API_KEY")

PROFILE_NAME = config("BAIKALCTL_PROFILE_NAME", cast=str, default="default")
PROFILE_DIR = config("BAIKALCTL_PROFILE_DIR", cast=str, default=str(Path.home() / ".cache" / "baikalctl" / "profile"))
PROFILE_CREATE_TIMEOUT = config("BAIKALCTL_PROFILE_CREATE_TIMEOUT", cast=int, default=30)
PROFILE_STABILIZE_TIME = config("BAIKALCTL_PROFILE_STABILIZE_TIME", cast=int, default=2)

DEBUG = config("DEBUG", cast=bool, default=False)
LOG_LEVEL = config("LOG_LEVEL", cast=str, default="WARNING")
VERBOSE = config("VERBOSE", cast=bool, default=False)
