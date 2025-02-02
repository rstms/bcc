# bcc API client

from typing import Dict, List

import requests
from pydantic import validate_call
from requests.exceptions import JSONDecodeError

from . import settings
from .models import (
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


class API:
    @validate_call
    def __init__(
        self,
        *,
        url: str | None = None,
        admin_username: str | None = None,
        admin_password: str | None = None,
        client_cert: str | None = None,
        client_key: str | None = None,
        api_key: str | None = None,
    ):
        self.url = settings.get(url, "CALDAV_URL").strip("/")

        self.session = requests.Session()
        self.session.cert = (
            settings.get(client_cert, "CLIENT_CERT", settings.Get.VALIDATE_PEM_CERTIFICATE_FILE),
            settings.get(client_key, "CLIENT_KEY", settings.Get.VALIDATE_PEM_PRIVATE_KEY_FILE),
        )
        self.session.headers["X-Admin-Username"] = settings.get(admin_username, "ADMIN_USERNAME")
        self.session.headers["X-Admin-Password"] = settings.get(
            admin_password, "ADMIN_PASSWORD", settings.Get.DECODE_SECRET, settings.Get.OPTIONAL_READ_FILE
        )
        self.session.headers["X-Api-Key"] = settings.get(
            api_key, "API_KEY", settings.Get.DECODE_SECRET, settings.Get.OPTIONAL_READ_FILE
        )

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
