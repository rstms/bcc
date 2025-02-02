# test config

import asyncio
import os
import socket
import time
from threading import Thread

import psutil
import pytest

from bcc import settings
from bcc.app import app
from bcc.client import API
from bcc.models import Book, User

LISTEN_TIMEOUT = 5

TEST_PORT = 8001
TEST_API_KEY = os.environ.get("TEST_API_KEY", "test_api_key")


@pytest.fixture(scope="session", autouse=True)
def test_env():
    env = os.environ
    try:
        os.environ["LOG_LEVEL"] = "DEBUG"
        yield env
    finally:
        for k, v in env.items():
            os.environ[k] = v
    settings.ADDRESS = "127.0.0.1"
    settings.PORT = TEST_PORT
    settings.API_KEY = TEST_API_KEY


@pytest.fixture(scope="session")
def test_api_key():
    return TEST_API_KEY


@pytest.fixture
def headers():
    return {"X-API-Key": str(settings.API_KEY)}


class TestServer:
    def __init__(self, app):

        self.host = "127.0.0.1"
        self.port = TEST_PORT
        self.app = app
        self._server = None

    def run(self):
        import uvicorn

        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="debug",
            loop="asyncio",
            lifespan="on",
        )
        self._server = uvicorn.Server(config)
        self._server.run()

    def stop(self):
        if self._server:
            self._server.should_exit = True


async def listening(host, port):
    timeout = time.time() + LISTEN_TIMEOUT
    connected = False
    while not connected:
        assert time.time() < timeout, f"Timed out waiting for {host}:{port} LISTEN"
        try:
            socket.create_connection((host, port), timeout=1)
        except ConnectionRefusedError:
            await asyncio.sleep(1)
        else:
            connected = True


def listening_tcp_ports():
    return [conn.laddr.port for conn in psutil.net_connections(kind="tcp") if conn.status == "LISTEN"]


@pytest.fixture(scope="session")
async def test_server():
    use_existing = "USE_EXISTING_SERVER" in os.environ
    if int(TEST_PORT) in listening_tcp_ports():
        assert use_existing, f"server running on port {TEST_PORT}; set USE_EXISTING_SERVER to use"
        yield True
        return
    server = TestServer(app)
    thread = Thread(target=server.run)
    thread.start()
    try:
        await listening(server.host, server.port)
        yield server
    finally:
        server.stop()
        thread.join()


@pytest.fixture(scope="session")
def test_url():
    return f"http://localhost:{TEST_PORT}"


@pytest.fixture(scope="session")
def client(test_server, test_url):
    client = API()
    yield client


@pytest.fixture(scope="module")
def testid():
    yield str(time.time()).replace(".", "")


@pytest.fixture(scope="module")
def username(testid):
    return f"t{testid}@domain.ext"


@pytest.fixture(scope="module")
def displayname(testid):
    return f"testuser {testid}"


@pytest.fixture(scope="module")
def password(testid):
    return testid


@pytest.fixture(scope="module")
def bookname(testid):
    return f"book_{testid}"


@pytest.fixture(scope="module")
def description(testid):
    return f"test book {testid}"


@pytest.fixture(scope="module")
def testuser(client, username, displayname, password):
    original_users = {u.username: u for u in client.users()}
    original_books = {u: {b.token: b for b in client.books(u)} for u in original_users}
    user = client.add_user(username, displayname, password)
    assert isinstance(user, User)
    yield user
    users = client.users()
    for user in users:
        if user.username not in original_users:
            client.delete_user(user.username)
        else:
            for book in client.books(user.username):
                if book.token not in original_books[user.username]:
                    client.delete_book(user.username, book.token)


@pytest.fixture(scope="module")
def testbook(client, testuser, bookname, description):
    book = client.add_book(testuser.username, bookname, description)
    assert isinstance(book, Book)
    yield book
