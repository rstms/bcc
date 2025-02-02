import logging
import os
import signal
from contextlib import asynccontextmanager

import arrow
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from typing_extensions import Annotated

from . import settings
from .browser import BrowserException, Session
from .models import (
    Account,
    AddBookRequest,
    AddBookResponse,
    AddUserRequest,
    AddUserResponse,
    BooksResponse,
    DeleteBookRequest,
    DeleteBookResponse,
    DeleteUserRequest,
    DeleteUserResponse,
    InitializeResponse,
    ResetResponse,
    ShutdownResponse,
    StatusResponse,
    UptimeResponse,
    UsersResponse,
)
from .version import __version__

log = logging.getLogger("uvicorn")


async def required_headers(
    x_admin_username: Annotated[str, Header()],
    x_admin_password: Annotated[str, Header()],
    x_api_key: Annotated[str, Header()],
):
    if x_api_key != app.state.api_key:
        raise HTTPException(status_code=401, detail="invalid API key")
    if not x_admin_username:
        raise HTTPException(status_code=401, detail="missing username")
    if not x_admin_password:
        raise HTTPException(status_code=401, detail="missing password")
    app.state.account = Account(username=x_admin_username, password=x_admin_password)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.setLevel(settings.LOG_LEVEL)
    log.info(f"bcc v{__version__} startup")
    app.state.api_key = str(settings.API_KEY)
    app.state.startup_time = arrow.now()
    app.state.session = Session()
    yield
    log.info("shutdown")
    app.state.session.shutdown()


app = FastAPI(dependencies=[Depends(required_headers)], lifespan=lifespan)


@app.exception_handler(BrowserException)
async def browser_exception_handler(request: Request, exc: BrowserException):
    path = str(request.url)[len(str(request.base_url)) :]
    return JSONResponse(
        status_code=500,
        content=dict(
            success=False, request=request.method + " /" + path, message=exc.__class__.__name__, detail=exc.args
        ),
    )


@app.middleware("http")
async def logout_after_request(request: Request, call_next):
    response = await call_next(request)
    app.state.session.logout()
    return response


@app.get("/status/")
async def get_status() -> StatusResponse:
    return StatusResponse(request="status", status=app.state.session.status(app.state.account))


@app.post("/reset/")
async def post_reset() -> ResetResponse:
    return app.state.session.reset(app.state.account)


@app.post("/initialize/")
async def post_initialize() -> InitializeResponse:
    return app.state.session.initialize(app.state.account)


@app.get("/users/")
async def get_users() -> UsersResponse:
    return UsersResponse(users=app.state.session.users(app.state.account))


@app.post("/user/")
async def post_user(request: AddUserRequest) -> AddUserResponse:
    return AddUserResponse(user=app.state.session.add_user(app.state.account, request))


@app.delete("/user/")
async def delete_user(request: DeleteUserRequest) -> DeleteUserResponse:
    return app.state.session.delete_user(app.state.account, request)


@app.get("/books/")
async def get_addressbooks_all() -> BooksResponse:
    users = app.state.session.users(app.state.account)
    books = []
    for user in users:
        books.extend(app.state.session.books(app.state.account, user.username))
    return BooksResponse(books=books)


@app.get("/books/{username}/")
async def get_addressbooks_user(username: str) -> BooksResponse:
    return BooksResponse(books=app.state.session.books(app.state.account, username))


@app.post("/book/")
async def post_address_book(request: AddBookRequest) -> AddBookResponse:
    return AddBookResponse(book=app.state.session.add_book(app.state.account, request))


@app.delete("/book/")
async def delete_book(request: DeleteBookRequest) -> DeleteBookResponse:
    return app.state.session.delete_book(app.state.account, request)


@app.post("/shutdown/")
async def shutdown(background_tasks: BackgroundTasks) -> ShutdownResponse:
    log.warning("received shutdown request")
    background_tasks.add_task(shutdown_app)
    return dict(message="shutdown requested")


def shutdown_app():
    log.warning("shutdown_task: exiting")
    os.kill(os.getpid(), signal.SIGINT)


@app.get("/uptime/")
async def uptime() -> UptimeResponse:
    return dict(message="started " + app.state.startup_time.humanize(arrow.now()))
