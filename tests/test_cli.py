# cli tests

import json
import os
import shlex

import pytest
from click.testing import CliRunner

import baikalctl as baikalctl_module
from baikalctl import __version__, bcc
from baikalctl.models import Book, User


@pytest.fixture
def run(test_url, test_api_key):
    runner = CliRunner()

    env = os.environ.copy()
    env["TESTING"] = "1"

    def _run(cmd, **kwargs):
        assert_exit = kwargs.pop("assert_exit", 0)
        assert_exception = kwargs.pop("assert_exception", None)
        parse_json = kwargs.pop("parse_json", True)
        env.update(kwargs.pop("env", {}))
        env.update({"BCC_URL": test_url, "BCC_API_KEY": test_api_key})
        kwargs["env"] = env
        result = runner.invoke(bcc, cmd, **kwargs)
        if assert_exception is not None:
            assert isinstance(result.exception, assert_exception)
        elif result.exception is not None:
            raise result.exception from result.exception
        elif assert_exit is not None:
            assert result.exit_code == assert_exit, (
                f"Unexpected {result.exit_code=} (expected {assert_exit})\n"
                f"cmd: '{shlex.join(cmd)}'\n"
                f"output: {str(result.output)}"
            )
        if parse_json:
            return json.loads(result.output)
        return result

    return _run


def test_cli_version():
    assert baikalctl_module.__name__ == "baikalctl"
    assert __version__
    assert isinstance(__version__, str)


def test_cli_status(run, client):
    result = run(["status"])
    assert isinstance(result, dict)
    print(result)


def test_cli_mkuser(run, client, username, displayname, password):
    result = run(["mkuser", username, displayname, password])
    assert isinstance(result, dict)
    user = User(**result)
    assert isinstance(user, User)
    assert user.username == username
    assert user.displayname == displayname
    client.delete_user(username)


def test_cli_users(run, client, testuser):
    result = run(["users"])
    assert len(result)
    assert isinstance(result, list)
    for r in result:
        assert isinstance(r, dict)
    users = [User(**r) for r in result]
    assert testuser.username in [u.username for u in users]


def test_cli_rmuser(run, client, testuser, password):
    result = run(["rmuser", testuser.username])
    assert result == dict(deleted_user=testuser.username)
    users = client.users()
    assert testuser.username not in [u.username for u in users]
    user = client.add_user(testuser.username, testuser.displayname, password)
    assert user


def test_cli_mkbook(run, client, testuser, bookname, description):
    result = run(["mkbook", testuser.username, bookname, description])
    assert isinstance(result, dict)
    book = Book(**result)
    assert isinstance(book, Book)
    client.delete_book(testuser.username, book.token)


def test_cli_books(run, client, testuser, testbook):
    results = run(["books"])
    assert isinstance(results, list)
    for result in results:
        assert isinstance(result, dict)
    books = [Book(**result) for result in results]
    assert testbook in books


def test_cli_rmbook(run, client, testuser, testbook):
    result = run(["rmbook", testuser.username, testbook.token])
    assert result == dict(request="delete address book", success=True, message=f"deleted_book: {testbook.token}")
