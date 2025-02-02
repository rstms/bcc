# baikalctl browser puppeteer

import logging
from typing import Any, Dict, List, Tuple

import arrow
from bs4 import BeautifulSoup
from pydantic import validate_call
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.support.ui import Select

from .firefox_profile import Profile
from .models import (
    VALID_TOKEN_CHARS,
    Account,
    AddBookRequest,
    AddUserRequest,
    Book,
    DeleteBookRequest,
    DeleteUserRequest,
    User,
)
from .version import __version__

LOG_SOUP = False


class BrowserException(Exception):
    pass


class BrowserInterfaceFailure(BrowserException):
    pass


class InitFailed(BrowserException):
    pass


class AddFailed(BrowserException):
    pass


class DeleteFailed(BrowserException):
    pass


class UnexpectedServerResponse(BrowserException):
    pass


class SessionConfig:
    debug = False
    log_level = "WARNING"
    logger = __name__
    create_profile = False

    @validate_call
    def __init__(  # noqa: C901
        self,
        *,
        url: str | None = None,
        cert: str | None = None,
        key: str | None = None,
        profile_name: str | None = None,
        profile_dir: str | None = None,
        profile_create_timeout: int | None = None,
        profile_stabilize_time: int | None = None,
        log_level: str | None = None,
        logger: str | Any = None,
        debug: bool | None = None,
        api_key: str | None = None,
    ):
        if url is not None:
            self.__class__.url = url
        if cert is not None:
            self.__class__.cert = cert
        if key is not None:
            self.__class__.key = key
        if profile_name is not None:
            self.__class__.profile_name = profile_name
        if profile_dir is not None:
            self.__class__.profile_dir = profile_dir
        if profile_create_timeout is not None:
            self.__class__.profile_create_timeout = profile_create_timeout
        if profile_stabilize_time is not None:
            self.__class__.profile_stabilize_time = profile_stabilize_time
        if logger is not None:
            self.__class__.logger = logger
        if log_level is not None:
            self.__class__.log_level = log_level
        if debug is not None:
            self.__class__.debug = debug
        if api_key is not None:
            self.__class__.api_key = api_key


class Session:

    def __init__(self, **kwargs):

        config = SessionConfig(**kwargs)

        if isinstance(config.logger, str):
            self.logger = logging.getLogger(config.logger)
        else:
            self.logger = config.logger

        self.logger.setLevel(config.log_level)

        self.logger.info("startup")
        self.driver = None
        self.logged_in = False
        self.startup_time = arrow.now()
        self.reset_time = None

        self.url = config.url
        self.profile = Profile(
            config.profile_name,
            config.profile_dir,
            config.profile_create_timeout,
            config.profile_stabilize_time,
            logger=self.logger,
        )
        self.cert_file = config.cert
        self.key_file = config.key
        self.profile.AddCert(config.cert, config.key)
        self.debug = config.debug
        self.api_key = config.api_key

    def _load_driver(self):
        if not self.driver:
            self.firefox_options = webdriver.FirefoxOptions()
            self.firefox_options.profile = FirefoxProfile(self.profile.dir)
            self.firefox_options.profile.set_preference("security.default_personal_cert", "Select Automatically")
            self.driver = webdriver.Firefox(options=self.firefox_options)

    def shutdown(self):
        self.logger.info("shutdown")
        if self.logged_in:
            self.logout()
        if self.driver:
            self.driver.quit()
            self.driver = None

    @validate_call
    def _find_elements(
        self,
        name: str,
        selector: str,
        *,
        parent: Any | None = None,
        with_text: str | None = None,
        allow_none: bool | None = False,
        click: bool | None = False,
    ) -> List[Any]:
        if parent is None:
            parent = self.driver
        try:
            elements = parent.find_elements(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            if allow_none:
                return []
            raise BrowserInterfaceFailure(f"{name} not found: {selector=} {with_text=}")

        if elements is not None:
            if with_text:
                elements = [element for element in elements if element.text == with_text]
            if elements:
                if click:
                    elements[0].click()
                return elements
            if allow_none:
                return elements
        raise BrowserInterfaceFailure(f"{name} not found: {selector=} {with_text=}")

    @validate_call
    def _find_element(
        self,
        name: str,
        selector: str,
        *,
        parent: Any | None = None,
        with_text: str | None = None,
        with_classes: List[str] | None = [],
    ) -> Any:
        if parent is None:
            parent = self.driver
        try:
            element = parent.find_element(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            raise BrowserInterfaceFailure(f"{name} not found: {selector=} {with_text=}")

        if element:
            if with_text:
                if element.text != with_text:
                    raise BrowserInterfaceFailure(f"{name} text mismatch: expected='{with_text}' got='{element.text}'")
            if with_classes:
                classes = element.get_attribute("class").split(" ")
                for cls in with_classes:
                    if cls not in classes:
                        raise BrowserInterfaceFailure(
                            f"{name} expected class not found: expected={cls} classes={classes} {selector=}"
                        )
            return element
        raise BrowserInterfaceFailure(f"{name} element not found: {selector=}")

    @validate_call
    def _click_button(self, name: str, selector: str, *, parent: Any | None = None, with_text: str | None = None):
        if with_text is not None:
            self._find_elements(name, selector, parent=parent, with_text=with_text, click=True)
        else:
            self._find_element(name, selector, parent=parent, with_text=with_text).click()

    @validate_call
    def _check_popups(self, require_none: bool | None = False) -> List[str]:
        messages = self._find_elements("popup messages", 'html > body [id="message"]', allow_none=True)
        ret = [message.text for message in messages]
        if ret and require_none:
            raise UnexpectedServerResponse("\n".join(ret).replace("\n", ": "))
        return ret

    @validate_call
    def _set_text(self, name: str, selector: str, text: str | None):
        element = self._find_element(name, selector)
        element.clear()
        if text:
            element.send_keys(text)

    @validate_call
    def _get(self, path: str):
        self._load_driver()
        url = self.url + path
        self.logger.info(f"GET {url}")
        try:
            self.driver.get(url)
        except WebDriverException as ex:
            raise BrowserInterfaceFailure(ex.msg)

        if LOG_SOUP:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            source = soup.prettify()
            for line in source.split("\n"):
                self.logger.debug(line)

    @validate_call
    def login(self, admin: Account):
        if self.logged_in == admin.username:
            return
        self.logger.info("login")

        self._get("/admin/")

        if self.driver.title == "Baïkal Maintainance":
            raise BrowserInterfaceFailure("server not initialized")

        self.logger.info(f"connected to {self.driver.title}")

        self._set_text("login username field", 'body form input[id="login"]', admin.username)
        self._set_text("login password field", 'body form input[id="password"]', admin.password)
        self._click_button("login authenticate button", "body form button", with_text="Authenticate")
        self._check_popups(require_none=True)
        self.logged_in = admin.username
        self.logger.info(f"Successfull login as '{admin.username}'")

    @validate_call
    def initialize(self, admin: Account) -> Dict[str, str]:
        self.logger.info("initialize")

        self._get("/admin/install/")
        if self.driver.title == "" and "Installation was already completed." in self.driver.page_source:
            raise InitFailed("already initialized")

        if self.driver.title != "Baïkal Maintainance":
            raise BrowserInterfaceFailure(f"unexpected page title: {self.driver.title}")

        while True:
            if self._find_elements(
                "start button",
                "body .btn-success",
                with_text="Start using Baïkal",
                allow_none=True,
                click=True,
            ):
                if self.driver.current_url.endswith("/baikal/admin/"):
                    return dict(message="initialized")
                else:
                    raise InitFailed("unexpected url after start button: {self.driver.current_url}")
            jumbotron = self._find_element("initialization title", "body .jumbotron")
            title_text = jumbotron.text.lower()
            if "database setup" in title_text:
                self._click_button("database init save changes button", "body form .btn", with_text="Save changes")
            elif "initialization wizard" in title_text:
                timezone = self._find_element("init timezone selector", 'body form select[name="data[timezone]"]')
                select = Select(timezone)
                select.select_by_visible_text("UTC")
                self._set_text("init invite address", 'body form input[name="data[invite_from]"]', None)
                self._set_text(
                    "init admin password",
                    'body form input[name="data[admin_passwordhash]"]',
                    admin.password,
                )
                self._set_text(
                    "init admin password confirmation",
                    'body form input[name="data[admin_passwordhash_confirm]"]',
                    admin.password,
                )
                self._click_button("general init save changes button", "body form .btn", with_text="Save changes")
            else:
                raise InitFailed(f"unexpected init title: {jumbotron.text}")

        BrowserInterfaceFailure("initialization failed")

    # new
    def logout(self):
        if self.logged_in:
            self.logger.info("logout")
            self._get("/admin/")
            self._click_navbar_link("Logout")
            self.logged_in = False

    # new
    def _select_user_page(self):
        self._get("/admin/")
        self._click_navbar_link("Users and resources")

    # new
    @validate_call
    def _click_navbar_link(self, label: str):
        navbars = self._find_elements("navbar", "div.navbar")
        if len(navbars) != 1:
            raise BrowserInterfaceFailure("multiple navbars located")
        links = {e.text: e for e in self._find_elements("navbar links", "a", parent=navbars[0]) if e.text}
        link = links.get(label, None)
        if label not in links:
            raise BrowserInterfaceFailure(f"navbar link not found: expected={label} links={list(links.keys())}")
        link.click()

    # new
    @validate_call
    def _table_rows(self, name: str, allow_none: bool | None = True):
        # table = self._find_element(f"{name} table",  "body table", with_classes=["table", name])
        # tbody = self._find_element(f"{name} table body",  "tbody", parent=table)
        rows = self._find_elements(f"{name} table body rows", "body table tbody tr", allow_none=True)
        if not rows:
            message = f"no {name} table body rows found"
            if allow_none:
                self.logger.warning(message)
            else:
                raise BrowserInterfaceFailure(message)
        return rows

    # new
    @validate_call
    def _parse_user_row(self, row: Any) -> Dict[str, str]:
        col_username = self._find_element("user table row displayname column", "td.col-username", parent=row)
        username, _, tail = col_username.text.partition("\n")
        displayname, _, email = tail.partition(" <")
        email = email.strip(">")
        ret = self._parse_row_info("user", row)
        ret.update(dict(username=username, displayname=displayname, email=email))
        return ret

    # new
    @validate_call
    def _parse_book_row(self, row: Any) -> Dict[str, str]:
        ret = {}
        col_displayname = self._find_element("book table row displayname column", "td.col-displayname", parent=row)
        ret["bookname"] = col_displayname.text
        col_contacts = self._find_element("book table row contacts column", "td.col-contacts", parent=row)
        ret["contacts"] = int(col_contacts.text)
        col_description = self._find_element("book table row description column", "td.col-description", parent=row)
        ret["description"] = col_description.text
        data = self._parse_row_info("addressbooks", row)
        ret.update(data)
        ret["token"] = ret["uri"].split("/")[-2]
        return ret

    # new
    @validate_call
    def _parse_row_info(self, name: str, row: Any) -> Dict[str, str]:
        actions = self._find_element(f"{name} table row actions column", "td.col-actions", parent=row)
        popover = self._find_element(f"{name} table row actions popover data", "span.btn.popover-hover", parent=actions)
        data_content = popover.get_attribute("data-content")
        soup = BeautifulSoup(data_content, "html.parser")
        ret = {}
        last_line = None
        for line in soup.strings:
            if last_line == "URI":
                ret["uri"] = line
            elif last_line == "User name":
                ret["username"] = line
            last_line = line
        if "uri" not in ret:
            raise BrowserInterfaceFailure(f"{name} table row info parse failed")
        return ret

    # new
    @validate_call
    def _row_action_buttons(self, name: str, row: Any) -> Dict[str, Any]:
        actions = self._find_element(f"{name} table row actions column", "td.col-actions", parent=row)
        action_buttons = self._find_elements(f"{name} table row actions buttons", "a.btn", parent=actions)
        buttons = {e.text: e for e in action_buttons if e.text}
        return buttons

    # new
    @validate_call
    def users(self, admin: Account) -> List[User]:
        self.logger.info("list_users")
        self.login(admin)
        self._select_user_page()
        rows = self._table_rows("users")
        return [User(**self._parse_user_row(row)) for row in rows]

    # old
    @validate_call
    def add_user(self, admin: Account, request: AddUserRequest) -> User:
        self.logger.info(f"add_user {request.username} {request.displayname} ************")
        user = User(**request.model_dump())
        self.login(admin)
        self._select_user_page()
        self._click_button("add user button", "body .btn", with_text="+ Add user")
        self._set_text("add user username field", 'body form input[name="data[username]"]', user.username)
        self._set_text("add user displayname field", 'body form input[name="data[displayname]"]', user.displayname)
        self._set_text("add user email field", 'body form input[name="data[email]"]', user.username)
        self._set_text("add user password field", 'body form input[name="data[password]"]', request.password)
        self._set_text(
            "add user password confirmation field",
            'body form input[name="data[passwordconfirm]"]',
            request.password,
        )
        self._click_button(
            "add user save changes button",
            "body form .btn",
            with_text="Save changes",
        )
        self._check_add_popups("user", f"User {user.username} has been created.")
        _, parsed = self._find_user_row(user.username, allow_none=False)
        added = User(**parsed)
        if added.username == request.username and added.displayname == request.displayname:
            return added
        raise AddFailed(
            f"added user mismatches request: added={repr(added.model_dump())} request={repr(request.model_dump())}"
        )

    @validate_call
    def _check_add_popups(self, name: str, expected: str):
        popups = self._check_popups()
        self._click_button(f"add {name} close button ", "body form .btn", with_text="Close")
        if expected in popups:
            return
        elif popups:
            message = ": ".join(popups).replace("\n", ": ")
        else:
            message = "missing add response"
        self.logger.error(message)
        raise AddFailed(message)

    # old
    @validate_call
    def delete_user(self, admin: Account, request: DeleteUserRequest) -> Dict[str, str]:
        username = request.username
        self.logger.info(f"delete_user {username}")
        self.login(admin)
        actions = self._find_user_actions(username)
        if not actions:
            raise DeleteFailed(f"user not found: {username=}")
        button = actions.get("Delete", None)
        if not button:
            raise BrowserInterfaceFailure("failed to locate Delete button")
        button.click()
        self._find_elements(
            "user delete confirmation button",
            "div.alert .btn-danger",
            with_text="Delete " + username,
            click=True,
        )
        return dict(message=f"deleted user: {username}")

    # new
    @validate_call
    def _find_user_row(self, username: str, allow_none: bool | None = True) -> Tuple[Any | None, Any | None]:
        self._select_user_page()
        rows = self._table_rows("users", allow_none=allow_none)
        for row in rows:
            user = self._parse_user_row(row)
            if user["username"] == username:
                return row, user
        self.logger.warning(f"user {username} not found")
        if allow_none:
            return None, None
        raise BrowserInterfaceFailure(f"failed to locate user row: {username=}")

    # new
    @validate_call
    def _find_user_actions(self, username: str, allow_none: bool | None = True) -> Dict[str, Any]:
        row, _ = self._find_user_row(username, allow_none=allow_none)
        if row:
            return self._row_action_buttons("user", row)
        return {}

    # new
    @validate_call
    def _select_user_address_books(self, username: str, allow_none: bool | None = True):
        buttons = self._find_user_actions(username, allow_none=allow_none)
        if buttons:
            buttons["Address Books"].click()
            return True
        return None

    # new
    @validate_call
    def _find_book_row(
        self, username: str, token: str, allow_none: bool | None = True
    ) -> Tuple[Any | None, Dict[str, Any] | None]:
        if not self._select_user_address_books(username, allow_none=allow_none):
            return None, None
        rows = self._table_rows("addressbooks")
        for row in rows:
            parsed = self._parse_book_row(row)
            if parsed["token"] == token:
                return row, parsed
        self.logger.warning(f"book {token} not found")
        return None, None

    # new
    @validate_call
    def _find_book_actions(self, username: str, token: str) -> Dict[str, Any]:
        row, _ = self._find_book_row(username, token)
        if row:
            return self._row_action_buttons("addressbook", row)
        return {}

    # new
    @validate_call
    def books(self, admin: Account, username: str) -> List[Book]:
        self.logger.info(f"list_address_books {username}")
        self.login(admin)
        if not self._select_user_address_books(username):
            return []
        rows = self._table_rows("addressbooks")
        ret = [Book(**self._parse_book_row(row)) for row in rows]
        return ret

    # old
    @validate_call
    def add_book(self, admin: Account, request: AddBookRequest) -> Book:
        self.logger.info(f"add_address_book {request.username} {request.bookname} {request.description}")
        self.login(admin)
        self._find_user_row(request.username, allow_none=False)
        token = request.username + "-" + request.bookname
        token = "".join([c if c in VALID_TOKEN_CHARS else "-" for c in token])
        book = Book(token=token, **request.model_dump())

        row, _ = self._find_book_row(book.username, book.token)
        if row is not None:
            raise AddFailed(f"address book exists: username={book.username} token={book.token}")

        self._select_user_address_books(book.username)
        self._click_button("add address book button", "body .btn", with_text="+ Add address book")
        self._set_text("add book token field", 'body form input[name="data[uri]"]', book.token)
        self._set_text("add book name field", 'body form input[name="data[displayname]"]', book.bookname)
        self._set_text("add book description field", 'body form input[name="data[description]"]', book.description)
        self._click_button("add book save changes button", "body form .btn", with_text="Save changes")
        self._check_add_popups("addressbook", f"Address Book {book.bookname} has been created.")
        _, parsed = self._find_book_row(request.username, token, allow_none=False)
        added = Book(**parsed)
        if (
            added.username == request.username
            and added.bookname == request.bookname
            and added.description == request.description
            and added.token == token
        ):
            return added
        raise AddFailed(
            f"added book mismatches request: added={repr(added.model_dump())} request={repr(request.model_dump())}"
        )

    @validate_call
    def delete_book(self, admin: Account, request: DeleteBookRequest) -> Dict[str, str]:
        self.logger.info(f"delete_address_book {request.username} {request.token}")
        self.login(admin)
        user_row, _ = self._find_user_row(request.username)
        if user_row is None:
            raise DeleteFailed(f"user not found: username={request.username}")
        row, book = self._find_book_row(request.username, request.token)
        if not row:
            raise DeleteFailed(f"book not found: username={request.username} token={request.token}")
        actions = self._row_action_buttons("addressbook", row)
        button = actions.get("Delete", None)
        if not button:
            raise BrowserInterfaceFailure("failed to locate address book Delete button")
        button.click()
        self._find_elements(
            "book delete confirmation button",
            "div.alert .btn-danger",
            with_text="Delete " + book["bookname"],
            click=True,
        )
        return dict(message=f"deleted_book: {request.token}")

    @validate_call
    def reset(self, admin: Account) -> Dict[str, str]:
        self.logger.info("reset")
        self.shutdown()
        self.login(admin)
        self.reset_time = arrow.now()
        return dict(message="server reset")

    @validate_call
    def status(self, admin: Account) -> Dict[str, str]:
        self.logger.info("status")

        try:
            self.login(admin)
            login = "success"
        except Exception as e:
            login = f"failed: {repr(e)}"

        return dict(
            name="baikalctl",
            version=__version__,
            driver=repr(self.driver),
            url=self.url,
            uptime=self.startup_time.humanize(),
            reset=self.reset_time.humanize() if self.reset_time else "never",
            profile_dir=self.profile.name if self.profile else None,
            certificates=repr(list(self.profile.ListCerts().keys()) if self.profile else None),
            certificate_loaded=self.cert_file,
            login=login,
        )
