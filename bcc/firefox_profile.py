# firefox profile

import logging
import shlex
import subprocess
import tempfile
import time
from pathlib import Path


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


def commonName(cert):
    with tempfile.NamedTemporaryFile(suffix=".pem") as tf:
        pemCert = cert
        if Path(cert).suffix == ".p12":
            run(f"openssl pkcs12 -in {str(cert)} -nokeys -out {tf.name} -password pass:")
            pemCert = tf.name
        cmd = f"openssl x509 -in {pemCert} -noout -subject"
        out = subprocess.check_output(shlex.split(cmd))
        out = out.decode().strip()
        if out.lower().startswith("subject=cn"):
            prefix, _, name = out.partition("=CN")
            name = name.strip(" =")
            return name
        raise RuntimeError(f"Failed to parse subject CN from certificate {cert} {repr(out)}")


class Profile:

    def __init__(self, name, dir, create_timeout, stabilize_time, logger=None):
        if logger is None:
            logger = __name__
        if isinstance(logger, str):
            self.logger = logging.getLogger(logger)
        else:
            self.logger = logger
        self.name = name
        self.dir = Path(dir)
        self.create_timeout = create_timeout
        self.stabilize_time = stabilize_time
        self.dir.mkdir(parents=True, exist_ok=True)
        if countFiles(self.dir) < 3:
            self.create()

    def create(self):
        self.logger.info("Creating profile...")
        run(f"/usr/bin/firefox --headless --createprofile '{self.name} {self.dir}'")
        proc = subprocess.Popen(shlex.split(f"/usr/bin/firefox --headless --profile {self.dir} --first-startup"))
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
