"""baikalctl client cli"""

import json
import logging
import socket
import sys
from collections.abc import Iterable

import click

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


DEFAULT_URL = "https://mabctl." + ".".join(socket.getfqdn().split(".")[1:]) + "/baikalctl"
DEFAULT_CERT = "/etc/ssl/client.pem"
DEFAULT_KEY = "/etc/ssl/client.key"


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
@click.option("-U", "--username", envvar="BCC_USERNAME", default="admin", help="username (default: admin)")
@click.option("-P", "--password", envvar="BCC_PASSWORD", help="password")
@click.option("-u", "--url", envvar="BCC_URL", default=DEFAULT_URL, help="baikalctl server URL")
@click.option("-l", "--log-level", envvar="LOG_LEVEL", default="WARNING", help="server log level (default: WARNING)")
@click.option("--cert", envvar="BCC_CERT", default=DEFAULT_CERT, help="cient certificate file")
@click.option("--key", envvar="BCC_KEY", default=DEFAULT_KEY, help="client certificate key file")
@click.option("--api-key", envvar="BCC_API_KEY", help="baikalctl API key")
@click.option("--show-config", is_flag=True)
@click.option(
    "--shell-completion",
    is_flag=False,
    flag_value="[auto]",
    callback=_shell_completion,
    help="configure shell completion",
)
@click.pass_context
def bcc(
    ctx,
    debug,
    username,
    password,
    url,
    cert,
    key,
    api_key,
    log_level,
    show_config,
    shell_completion,
):
    """bcc - baikal controller client""" ""

    if show_config:
        click.echo(f"url: {url}")
        click.echo(f"username: {username}")
        click.echo(f"password: {'*'*len(password) if password else None}")
        click.echo(f"cert: {cert}")
        click.echo(f"key: {key}")
        click.echo(f"log_level: {log_level}")
        click.echo(f"debug: {debug}")
        sys.exit(0)

    logging.basicConfig(level=log_level)
    ctx.obj = API(url, username, password, cert, key, api_key)


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


if __name__ == "__main__":
    sys.exit(bcc())  # pragma: no cover
