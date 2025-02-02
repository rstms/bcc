# firefox profile

import logging
import os
import shlex
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from pydantic import validate_call

from . import settings


def countFiles(dir):
    dir = Path(dir)
    if dir.is_dir():
        return len(list(Path(dir).glob("*")))
    return -1


def mklist(out):
    lines = []
    for line in [line.strip() for line in out.decode().split("\n")]:
        if not line:
            continue
        if line.startswith("Certificate Nickname"):
            continue
        if line.startswith("SSL,S/MIME"):
            continue
        lines.append(line)
    return [line for line in lines if line and line]


def run(cmd, **kwargs):
    kwargs.setdefault("check", True)
    return subprocess.run(shlex.split(cmd), **kwargs)


def commonName(filename):
    certificate_file = Path(filename)
    suffix = certificate_file.suffix
    if suffix == ".pem":
        data = certificate_file.read_bytes()
        certificate = x509.load_pem_x509_certificate(data, default_backend())
        cn = certificate.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
        if cn:
            return cn[0].value
    elif suffix == ".p12":
        raise RuntimeError(f"cannot read pkcs12 cert: {filename}")
        # run(f"openssl pkcs12 -in {str(cert)} -nokeys -out {tf.name} -password pass:")
        #    pemCert = tf.name
    else:
        raise RuntimeError(f"unknown certificate format: {filename}")
    raise RuntimeError(f"Failed to parse subject CN from certificate {filename}")


class Profile:

    @validate_call
    def __init__(
        self,
        *,
        name: str | None = None,
        dir: str | None = None,
        create_timeout: int | None = None,
        stabilize_time: int | None = None,
        logger: Any | None = None,
    ):

        if isinstance(logger, str):
            self.logger = logging.getLogger(logger)
        elif logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)

        self.name = settings.get(name, "PROFILE_NAME")
        self.dir = Path(settings.get(dir, "PROFILE_DIR"))
        self.create_timeout = settings.get(create_timeout, "PROFILE_CREATE_TIMEOUT")
        self.stabilize_time = settings.get(stabilize_time, "PROFILE_STABILIZE_TIME")
        self.dir.mkdir(parents=True, exist_ok=True)
        if countFiles(self.dir) < 3:
            self.create()

    def mkenv(self):
        env = {k: v for k, v in os.environ.items()}
        env["DISPLAY"] = settings.DISPLAY
        return env

    def create(self):
        self.logger.info("Creating profile...")
        run(f"{settings.FIREFOX_BIN} --headless --createprofile '{self.name} {self.dir}'", env=self.mkenv())

        proc = subprocess.Popen(
            shlex.split(f"{settings.FIREFOX_BIN} --headless --profile {self.dir} --first-startup"), env=self.mkenv()
        )
        timeout_tick = time.time() + self.create_timeout
        stable = 0
        lastcount = 0
        while stable <= self.stabilize_time:
            if time.time() > timeout_tick:
                raise RuntimeError("timeout waiting for profile init")
            if proc.poll() is not None:
                raise RuntimeError("firefox exited unexpectedly")
            count = countFiles(self.dir)
            if count == lastcount:
                stable += 1
            else:
                stable = 0
            lastcount = count
            time.sleep(1)
        proc.kill()
        proc.wait()
        self.logger.info(f"Profile {self.name} written to {self.dir}")

    def ListCerts(self):
        certlist = mklist(subprocess.check_output(shlex.split(f"certutil -L -d sql:{str(self.dir)}")))
        certs = {}
        for certline in certlist:
            fields = certline.split()
            key = " ".join(fields[:-1])
            value = fields[-1]
            certs[key] = value
        return certs

    def AddCert(self, cert, key=None):
        certName = commonName(cert)
        self.logger.info("Adding client certificate...")
        with tempfile.NamedTemporaryFile(suffix=".p12") as tf:
            if Path(cert).suffix != ".p12":
                cmd = f"openssl pkcs12 -export -in {str(cert)} -inkey {str(key)} -out {tf.name} -passout pass:"
                run(cmd)
                cert = tf.name
            cmd = f"pk12util -i {cert} -n '{certName}' -d sql:{str(self.dir)} -W ''"
            run(cmd)
        self.logger.info(f"Certificate {certName} added to profile {self.name}.")
        return certName
