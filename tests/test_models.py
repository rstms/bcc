import pytest
from pydantic import ValidationError

from bcc.models import (
    Account,
    AddBookRequest,
    AddUserRequest,
    Book,
    DeleteBookRequest,
    DeleteUserRequest,
    User,
)


@pytest.fixture
def valid_emails():
    return [
        "name@domain.ext",
        "name@one.domain.ext",
        "name@one.two.domain.ext",
        "name-dot@domain.ext",
        "name-dash@domain.ext",
        "name%percent@domain.ext",
        "name+plus@domain.ext",
    ]


@pytest.fixture
def invalid_emails():
    return [
        "plainaddress",  # Missing '@' and domain
        "@missingusername.com",  # Missing username
        "missingatsign.com",  # Missing '@'
        "username@.com",  # Domain missing before the dot
        "username@domain..com",  # Consecutive dots in the domain
        "username@domain.c",  # TLD is too short (1 character)
        "user@domain-.com",  # Hyphen at the end of a domain
        "user@.domain.com",  # Dot immediately after the '@'
        "user@domain.com.",  # Trailing dot in the email
        "user@domain..com",  # Consecutive dots in the domain part
    ]


@pytest.fixture
def invalid_passwords():
    return ["short", " startspace", "endspace ", "embedded space", "", 1, None]


def test_models_account(invalid_passwords):
    account = Account(username="username", password="password")
    assert isinstance(account, Account)
    with pytest.raises(ValidationError):
        _ = Account()
    with pytest.raises(ValidationError):
        _ = Account(username="ok")
    with pytest.raises(ValidationError):
        _ = Account(password="password")
    for password in invalid_passwords:
        with pytest.raises(ValidationError):
            _ = Account(username="valid", password=password)


def test_models_user(valid_emails, invalid_emails):
    for email in valid_emails:
        user = User(username=email, displayname="user name")
        assert isinstance(user, User)
        no_display = User(username=email)
        assert isinstance(no_display, User)

    for bad_email in invalid_emails:
        with pytest.raises(ValidationError):
            _ = User(username=bad_email)


def test_models_book():
    book = Book(username="name@domain.com", bookname="address_book_name", description="address book description")
    assert isinstance(book, Book)


def test_models_add_user():
    request = AddUserRequest(username="name@domain.com", displayname="user name", password="password")
    assert isinstance(request, AddUserRequest)


def test_models_delete_user():
    request = DeleteUserRequest(username="name@domain.com")
    assert isinstance(request, DeleteUserRequest)


def test_models_add_book():
    request = AddBookRequest(
        username="name@domain.com", bookname="address_book_name", description="address book description"
    )
    assert isinstance(request, AddBookRequest)


def test_models_delete_book():
    request = DeleteBookRequest(username="name@domain.com", token="this-is-a-token-1234")
    assert isinstance(request, DeleteBookRequest)
