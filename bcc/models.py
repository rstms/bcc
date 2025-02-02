# models

import string
from typing import Any, Dict, List

from pydantic import BaseModel, Field, ValidationInfo, model_validator

MIN_PASSWORD_LENGTH = 8
VALID_TOKEN_CHARS = string.ascii_lowercase + string.digits + "-"

_re_name = "[a-zA-Z][a-zA-Z0-9\\._%+-]*[a-zA-Z0-9]"
_re_domain = "([a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]{1,}\\.){1,}[a-zA-Z]{2,}"

regex_name = "^" + _re_name + "$"
regex_email = "^" + _re_name + "@" + _re_domain + "$"
regex_description = "^[a-zA-Z][a-zA-Z0-9@\\._ -]*[a-zA-Z0-9]*$|^$"
regex_password = "^\\S{" + str(MIN_PASSWORD_LENGTH) + ",}$"
regex_token = "^[a-z0-9-]+$|^$"


class Model(BaseModel):

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, value: Any, info: ValidationInfo) -> Any:
        if isinstance(value, dict):
            fields = value.keys()
            for field in fields:
                if value[field] is None:
                    value[field] = ""
                if isinstance(value[field], bytes):
                    value[field] = value[field].decode()
                if isinstance(value[field], str) and field != "password":
                    value[field] = value[field].strip()
                if field in ["username", "bookname", "token"]:
                    value[field] = value[field].lower()
        else:
            raise RuntimeError(f"model_validator: unexpected value type {type(value)} {value=} {info=}")
        return value


class Account(Model):
    username: str = Field(..., pattern=regex_name)
    password: str = Field(..., pattern=regex_password)


class User(Model):
    username: str = Field(..., pattern=regex_email)
    displayname: str | None = Field("", pattern=regex_description)
    uri: str | None = Field("")


class BookBase(Model):
    username: str = Field(..., pattern=regex_email)
    bookname: str = Field(..., pattern=regex_description)
    description: str | None = Field(None, pattern=regex_description)
    contacts: int | None = Field(0)
    uri: str | None = Field("")


class Book(BookBase):
    token: str = Field(None, pattern=regex_token)


class Response(BaseModel):
    success: str | bool | None = Field(True)
    request: str | None = Field("")
    message: str


class AddUserRequest(User):
    password: str = Field(..., pattern=regex_password)


class AddUserResponse(Response):
    request: str | None = Field("add user")
    message: str | None = Field("user added")
    user: User


class DeleteUserRequest(Model):
    username: str = Field(..., pattern=regex_email)


class DeleteUserResponse(Response):
    request: str | None = Field("delete user")


class AddBookRequest(BookBase):
    pass


class AddBookResponse(Response):
    request: str | None = Field("add address book")
    message: str | None = Field("address book added")
    book: Book


class DeleteBookRequest(Model):
    username: str = Field(..., pattern=regex_email)
    token: str = Field(..., pattern=regex_token)


class DeleteBookResponse(Response):
    request: str | None = Field("delete address book")


class UsersResponse(Response):
    request: str | None = Field("list users")
    message: str | None = Field("user list")
    users: List[User]


class BooksResponse(Response):
    request: str | None = Field("list address books")
    message: str | None = Field("address book list")
    books: List[Book]


class StatusResponse(Response):
    request: str | None = Field("status")
    message: str | None = Field("server status")
    status: Dict[str, Any]


class InitializeResponse(Response):
    request: str | None = Field("initialize")


class ShutdownResponse(Response):
    request: str | None = Field("shutdown")


class UptimeResponse(Response):
    request: str | None = Field("uptime")


class ResetResponse(Response):
    request: str | None = Field("reset")


class ErrorResponse(Response):
    success: bool | None = Field(False)
    message: str | None = Field("RequestFailed")
    detail: str | None = Field("unspecified error")
