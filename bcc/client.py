# baikalctl API client

import re
from pathlib import Path
from typing import Dict, List

import requests
from pydantic import validate_call
from requests.exceptions import JSONDecodeError

from .models import (
    Account,
    AddBookRequest,
    AddBookResponse,
    AddUserRequest,
    AddUserResponse,
    Book,
    BooksResponse,
    DeleteBookRequest,
    DeleteUserRequest,
    StatusResponse,
    User,
    UsersResponse,
)


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


class API:
    @validate_call
    def __init__(
        self, url: str, admin_username: str, admin_password: str, client_cert: str, client_key: str, api_key: str
    ):
        self.url = url.strip("/")
        self.session = requests.Session()
        validate_pem_file(client_cert, "certificate")
        validate_pem_file(client_key, "private key")
        self.session.cert = (client_cert, client_key)
        account = Account(username=admin_username, password=admin_password)
        self.session.headers["X-Admin-Username"] = account.username
        self.session.headers["X-Admin-Password"] = account.password
        self.session.headers["X-Api-Key"] = api_key

    def _parse_response(self, response):
        if response.ok:
            return response.json()
        try:
            message = response.json()
        except JSONDecodeError:
            message = f"{str(response)} {response.reason}"
        raise RuntimeError(message)

    def _request(self, func, path, **kwargs):
        return self._parse_response(func(f"{self.url}/{path.strip('/')}/", **kwargs))

    def _get(self, path, **kwargs):
        return self._request(self.session.get, path, **kwargs)

    def _post(self, path, **kwargs):
        return self._request(self.session.post, path, **kwargs)

    def _delete(self, path, **kwargs):
        return self._request(self.session.delete, path, **kwargs)

    @validate_call
    def status(self) -> Dict[str, str]:
        response = StatusResponse(**self._get("status"))
        return response.status

    @validate_call
    def initialize(self) -> Dict[str, str]:
        return self._post("initialize")

    @validate_call
    def reset(self) -> Dict[str, str]:
        return self._post("reset")

    @validate_call
    def users(self) -> List[User]:
        response = UsersResponse(**self._get("users"))
        return response.users

    @validate_call
    def add_user(self, username: str, displayname: str, password: str) -> User:
        request = AddUserRequest(username=username, displayname=displayname, password=password)
        response = AddUserResponse(**self._post("user", data=request.model_dump_json()))
        return response.user

    @validate_call
    def delete_user(self, username: str) -> Dict[str, str]:
        request = DeleteUserRequest(username=username)
        return self._delete("user", data=request.model_dump_json())

    @validate_call
    def books(self, username: str | None = None) -> List[Book]:
        if username:
            path = f"books/{username}"
        else:
            path = "books"
        result = BooksResponse(**self._get(path))
        return result.books

    @validate_call
    def add_book(self, username: str, bookname: str, description: str) -> Book:
        request = AddBookRequest(username=username, bookname=bookname, description=description)
        response = AddBookResponse(**self._post("book", data=request.model_dump_json()))
        return response.book

    @validate_call
    def delete_book(self, username: str, token: str) -> Dict[str, str]:
        request = DeleteBookRequest(username=username, token=token)
        return self._delete("book", data=request.model_dump_json())

    def shutdown(self):
        return self._post("shutdown")

    def uptime(self):
        return self._get("uptime")
