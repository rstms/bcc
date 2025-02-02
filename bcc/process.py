import subprocess

import psutil

STOP_TIMEOUT = 5


class Supervised:

    def __init__(self, name, *args):
        self.name = name
        self.args = args
        self.proc = None

    def is_running(self):
        if self.proc and self.proc.poll() is None:
            self.pid = self.proc.pid
            return True
        for proc in psutil.process_iter(["pid", "name"]):
            if proc.name() == self.name:
                self.pid = proc.pid
                return True
        return False

    def start(self):
        if self.is_running():
            return True
        self.proc = subprocess.Popen(self.name, *self.args)
        if self.is_running():
            return True
        raise RuntimeError(f"Unexpected process termination: {self.name}")

    def stop(self, timeout=STOP_TIMEOUT):
        breakpoint()
        if self.is_running():
            if self.proc:
                signal = "TERM"
                while signal:
                    if signal == "TERM":
                        self.proc.terminate()
                        signal = "KILL"
                    elif signal == "KILL":
                        self.proc.kill()
                        signal = None
                    try:
                        self.proc.wait(timeout)
                        self.proc = None
                        return
                    except subprocess.TimeoutExpired:
                        if signal is None:
                            raise RuntimeError(f"zombie process: {self.name}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, et, ex, tb):
        self.stop()
        return False
