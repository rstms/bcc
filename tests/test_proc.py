import time

from bcc.process import Supervised


def test_process_supervised():
    running = Supervised("Xvfb").is_running()
    assert running
    with Supervised("xterm"):
        time.sleep(5)
