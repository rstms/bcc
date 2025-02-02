# settings

import re
import socket
import subprocess
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import validate_call
from starlette.config import Config
from starlette.datastructures import Secret


class Get(Enum):
    OPTIONAL_READ_FILE = 1
    VALIDATE_PEM_CERTIFICATE_FILE = 2
    VALIDATE_PEM_PRIVATE_KEY_FILE = 3
    VALIDATE_PEM_PUBLIC_KEY_FILE = 4
    DECODE_SECRET = 5


default_webdriver_bin = subprocess.check_output("which geckodriver 2>/dev/null || true", shell=True, text=True).strip()
default_firefox_bin = subprocess.check_output("which firefox 2>/dev/null || true", shell=True, text=True).strip()

config = Config(".env")

ADDRESS = config("ADDRESS", cast=str, default="127.0.0.1")
PORT = config("PORT", cast=int, default=8000)

ADMIN_USERNAME = config("ADMIN_USERNAME", cast=str, default="admin")
ADMIN_PASSWORD = config("ADMIN_PASSWORD", cast=Secret)
API_KEY = config("API_KEY", cast=Secret)
CALDAV_URL = config(
    "CALDAV_URL", cast=str, default="http://caldav." + ".".join(socket.getfqdn().split(".")[1:]) + "/baikal"
)
BCC_URL = config("BCC_URL", cast=str, default="http://mabctl." + ".".join(socket.getfqdn().split(".")[1:]) + "/bcc")

CLIENT_CERT = config("CLIENT_CERT", cast=str, default=str(Path.home() / "certs" / "client.pem"))
CLIENT_KEY = config("CLIENT_KEY", cast=str, default=str(Path.home() / "certs" / "client.key"))

DISPLAY = config("DISPLAY", cast=str, default=":0")
FIREFOX_BIN = config("FIREFOX_BIN", cast=str, default="firefox")
PROFILE_NAME = config("PROFILE_NAME", cast=str, default="default")
PROFILE_DIR = config("PROFILE_DIR", cast=str, default=str(Path.home() / ".cache" / "bcc" / "profile"))
PROFILE_CREATE_TIMEOUT = config("PROFILE_CREATE_TIMEOUT", cast=int, default=30)
PROFILE_STABILIZE_TIME = config("PROFILE_STABILIZE_TIME", cast=int, default=2)
WEBDRIVER_BIN = config("WEBDRIVER_BIN", cast=str, default=default_webdriver_bin)
FIREFOX_BIN = config("FIREFOX_BIN", cast=str, default=default_firefox_bin)


HEADLESS = config("HEADLESS", cast=bool, default=True)
DEBUG = config("DEBUG", cast=bool, default=False)
LOG_LEVEL = config("LOG_LEVEL", cast=str, default="WARNING")
VERBOSE = config("VERBOSE", cast=bool, default=False)


def dotenv(reveal_passwords=False):
    ret = ""
    sep = ""
    for key in [k for k in globals().keys() if re.match("^[A-Z][A-Z_]*$", k)]:
        value = globals()[key]
        if isinstance(value, Secret):
            if reveal_passwords:
                value = str(value)
            else:
                value = "****************"
        if (not isinstance(value, str)) and str(value).isnumeric():
            value = str(value)
        if value is True:
            value = "1"
        elif value is False:
            value = "0"
        elif isinstance(value, str):
            if " " in value or "=" in value or '"' in value or "'" in value:
                value = "'" + value + "'"
        ret += f"{sep}{key}={value}"
        sep = "\n"
    return ret


def read_secret(value):
    if isinstance(value, Secret):
        value = str(value)
    if not value.startswith("@"):
        return value
    value = value[1:]
    if value.startswith("~"):
        path = Path.home()
        value = value[1:]
    else:
        path = Path(".")
    file = path / value
    value = file.read_text()
    value = value.strip()
    return value


def validate_pem_file(filename: str, pem_type: str):
    with Path(filename).open("r") as ifp:
        content = ifp.read()
        if "-----BEGIN" not in content or "-----END" not in content:
            raise ValueError(f"{filename} is not PEM format")
        if "cert" in pem_type:
            if not re.match(".*-----BEGIN CERTIFICATE-----.*", content, re.MULTILINE):
                raise ValueError(f"{filename} is not a certificate")
        elif "key" in pem_type:
            if "pub" in pem_type:
                if not re.match(".*-----BEGIN .*PUBLIC KEY-----.*", content, re.MULTILINE):
                    raise ValueError(f"{filename} is not a public key")
            elif "priv" in pem_type:
                if not re.match(".*-----BEGIN .*PRIVATE KEY-----.*", content, re.MULTILINE):
                    raise ValueError(f"{filename} is not a private key")
            else:
                if not re.match(".*-----BEGIN .* KEY-----.*", content, re.MULTILINE):
                    raise ValueError(f"{filename} is not a key")


@validate_call
def get(value: Any | None, name: str, *flags: Get) -> Any:
    """if value is None, set it from the named setting, performing post-processing if flags are set"""
    if value is None:
        value = globals()[name]
    for flag in flags:
        if flag == Get.DECODE_SECRET:
            if isinstance(value, Secret):
                value = str(value)
        elif flag == Get.OPTIONAL_READ_FILE:
            value = read_secret(value)
        elif flag == Get.VALIDATE_PEM_CERTIFICATE_FILE:
            validate_pem_file(value, "certificate")
        elif flag == Get.VALIDATE_PEM_PRIVATE_KEY_FILE:
            validate_pem_file(value, "privkey")
        elif flag == Get.VALIDATE_PEM_PUBLIC_KEY_FILE:
            validate_pem_file(value, "pubkey")
        else:
            raise ValueError(f"unrecognized settings flag: {flag}")
    return value
