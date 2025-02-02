import logging
from pathlib import Path

import pytest

from bcc import settings
from bcc.browser import Session
from bcc.firefox_profile import Profile, countFiles, run

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


@pytest.fixture
def keypair(shared_datadir):
    cert = shared_datadir / "test.pem"
    key = shared_datadir / "test.key"
    run(
        "openssl req -x509 -nodes -days 365 -newkey rsa:2048"
        f" -keyout {str(key)} -out {str(cert)} -subj '/CN=test_client_certificate'"
    )
    return (cert, key)


def test_profile_create(shared_datadir, keypair):
    pem, key = keypair
    assert pem.is_file()
    assert key.is_file()
    dir = shared_datadir / "profile"
    profile = Profile(dir=str(dir), logger=logger)
    assert dir.is_dir()
    assert dir == profile.dir
    assert len(list(dir.glob("*"))) > 3
    logger.info(f"profile created with {countFiles(dir)} files")

    before = profile.ListCerts()
    for i, cert in enumerate(before):
        logger.info(f"before[{i}]: {cert}")

    profile.AddCert(pem, key)
    after = profile.ListCerts()

    for i, cert in enumerate(after):
        logger.info(f"after[{i}]: {cert}")

    assert len(after) == len(before) + 1


def test_profile_driver():
    driver_bin = settings.WEBDRIVER_BINARY
    if driver_bin:
        assert Path(driver_bin).is_file()
    session = Session()
    session._load_driver()
    assert session.driver
    session.driver.get("https://duckduckgo.com")
    assert session.driver.title
    assert "DuckDuckGo" in session.driver.title
    session.shutdown()
