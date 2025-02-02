"""bcc cli"""

import json
import logging
import sys
from collections.abc import Iterable

import click
import uvicorn

from . import settings
from .client import API
from .exception_handler import ExceptionHandler
from .shell import _shell_completion
from .version import __timestamp__, __version__

header = f"{__name__.split('.')[0]} v{__version__} {__timestamp__}"

ehandler = None


def _ehandler(ctx, option, debug):
    global ehandler
    ehandler = ExceptionHandler(debug)
    return debug


def render(obj):
    if hasattr(obj, "model_dump_json"):
        return json.loads(obj.model_dump_json())
    if isinstance(obj, Iterable) and not (isinstance(obj, (str, bytes, dict))):
        return [render(o) for o in obj]
    else:
        return obj


def output(obj):
    click.echo(json.dumps(render(obj), indent=2))


@click.group("bcc")
@click.version_option(message=header)
@click.option("-d", "--debug", is_eager=True, envvar="DEBUG", is_flag=True, callback=_ehandler, help="debug mode")
@click.option("-u", "--username", help="username (default: admin)")
@click.option("-p", "--password", help="password")
@click.option("-U", "--url", help="caldav server URL")
@click.option("-l", "--log-level", help="server log level (default: WARNING)")
@click.option("-c", "--cert", help="cient certificate file")
@click.option("-k", "--key", help="client certificate key file")
@click.option("-a", "--api-key", help="bcc API key")
@click.option(
    "--shell-completion",
    is_flag=False,
    flag_value="[auto]",
    callback=_shell_completion,
    help="configure shell completion",
)
@click.pass_context
def bcc(ctx, debug, username, password, url, cert, key, api_key, log_level, shell_completion):
    """bcc - bcc control console"""

    if debug is not None:
        settings.DEBUG = True
    if username is not None:
        settings.USERNAME = username
    if password is not None:
        settings.PASSWORD = password
    if url is not None:
        settings.CALDAV_URL = url
    if cert is not None:
        settings.CLIENT_CERT = cert
    if key is not None:
        settings.CLIENT_KEY = key
    if api_key is not None:
        settings.API_KEY = api_key
    if log_level is not None:
        settings.LOG_LEVEL = log_level

    logging.basicConfig(level=log_level)

    if ctx.invoked_subcommand not in ["config", "server"]:
        ctx.obj = API()


@bcc.command
@click.pass_context
@click.option("--insecure", is_flag=True)
def config(ctx, insecure):
    """show configuration"""
    click.echo(settings.dotenv(reveal_passwords=insecure))
    sys.exit(0)


@bcc.command
@click.pass_obj
def users(ctx):
    """list users"""
    output(ctx.users())


@bcc.command
@click.argument("username")
@click.argument("display-name")
@click.argument("password")
@click.pass_obj
def mkuser(ctx, username, display_name, password):
    """add user account"""
    output(ctx.add_user(username, display_name, password))


@bcc.command
@click.argument("username")
@click.pass_obj
def rmuser(ctx, username):
    """delete user account"""
    output(ctx.delete_user(username))


@bcc.command
@click.argument("username", required=False)
@click.pass_obj
def books(ctx, username):
    """list address books for user"""
    output(ctx.books(username))


@bcc.command
@click.argument("username")
@click.argument("name")
@click.argument("description")
@click.pass_obj
def mkbook(ctx, username, name, description):
    """add address book for user"""
    output(ctx.add_book(username, name, description))


@bcc.command
@click.argument("username")
@click.argument("token")
@click.pass_obj
def rmbook(ctx, username, token):
    """delete address book for user"""
    output(ctx.delete_book(username, token))


@bcc.command
@click.pass_obj
def reset(ctx):
    """restart client driver"""
    output(ctx.reset())


@bcc.command
@click.pass_obj
def initialize(ctx):
    """initialize freshly installed server"""
    output(ctx.initialize())


@bcc.command
@click.pass_obj
def version(ctx):
    """print version number"""
    click.echo(__version__)


@bcc.command
@click.pass_obj
def status(ctx):
    """output status"""
    output(ctx.status())


@bcc.command
@click.pass_obj
def shutdown(ctx):
    """request server shutdown"""
    output(ctx.shutdown())


@bcc.command
@click.pass_obj
def uptime(ctx):
    """server uptime"""
    output(ctx.uptime())


@bcc.command
@click.pass_context
def server(ctx):
    """API server"""
    uvicorn.run(
        "bcc:app",
        host=settings.ADDRESS,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    sys.exit(bcc())  # pragma: no cover
