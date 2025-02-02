"""Console script for baikalctl."""

import sys

import click
import click.core
import uvicorn

from . import settings
from .browser import SessionConfig
from .exception_handler import ExceptionHandler
from .shell import _shell_completion
from .version import __timestamp__, __version__

header = f"{__name__.split('.')[0]} v{__version__} {__timestamp__}"


def _ehandler(ctx, option, debug):
    ctx.obj = dict(ehandler=ExceptionHandler(debug))
    return debug


@click.group("baikalctl", invoke_without_command=True)
@click.version_option(message=header)
@click.option(
    "-d", "--debug", is_eager=True, is_flag=True, callback=_ehandler, default=settings.DEBUG, help="debug mode"
)
@click.option("-l", "--log-level", default=settings.LOG_LEVEL, help="server log level (default: WARNING)")
@click.option("-U", "--url", default=settings.URL, help="caldav server URL")
@click.option("-A", "--address", default=settings.ADDRESS, help="server bind address (default: 0.0.0.0)")
@click.option("-P", "--port", type=int, default=settings.PORT, help="server listen port (default: 8000)")
@click.option("--profile-name", type=str, default=settings.PROFILE_NAME)
@click.option("--api_key", type=str, default=settings.API_KEY)
@click.option("--profile-dir", type=str, default=settings.PROFILE_DIR)
@click.option("--profile-create-timeout", type=int, default=settings.PROFILE_CREATE_TIMEOUT)
@click.option("--profile-stabilize-time", type=int, default=settings.PROFILE_STABILIZE_TIME)
@click.option("--cert", default=settings.CERT, help="cient certificate file")
@click.option("--key", default=settings.KEY, help="client certificate key file")
@click.option("--show-config", is_flag=True)
@click.option(
    "--shell-completion",
    is_flag=False,
    flag_value="[auto]",
    callback=_shell_completion,
    help="configure shell completion",
)
@click.pass_context
def baikalctl(
    ctx,
    url,
    cert,
    key,
    address,
    port,
    debug,
    log_level,
    profile_create_timeout,
    profile_stabilize_time,
    profile_dir,
    profile_name,
    show_config,
    shell_completion,
    api_key,
):
    """baikalctl - admin CLI for baikal webdav/webcal server"""

    if ctx.invoked_subcommand == "version":
        click.echo(__version__)
        sys.exit(0)

    if debug:
        log_level = "DEBUG"
    if log_level is not None:
        settings.LOG_LEVEL = log_level

    if show_config:
        click.echo(f"address: {address}")
        click.echo(f"port: {port}")
        click.echo(f"url: {url}")
        click.echo(f"cert: {cert}")
        click.echo(f"key: {key}")
        click.echo(f"profile_name: {profile_name}")
        click.echo(f"profile_dir: {profile_dir}")
        click.echo(f"profile_create_timeout: {profile_create_timeout}")
        click.echo(f"profile_stabilize_time: {profile_stabilize_time}")
        click.echo(f"log_level: {log_level}")
        click.echo(f"debug: {debug}")
        sys.exit(0)

    # logging.basicConfig(level=log_level)

    SessionConfig(
        url=url,
        cert=cert,
        key=key,
        profile_name=profile_name,
        profile_dir=profile_dir,
        profile_create_timeout=profile_create_timeout,
        profile_stabilize_time=profile_stabilize_time,
        debug=debug,
        logger="uvicorn",
        log_level=log_level,
        api_key=api_key,
    )

    uvicorn.run(
        "baikalctl:app",
        host=address,
        port=port,
        log_level=log_level.lower(),
    )


if __name__ == "__main__":
    sys.exit(baikalctl())  # pragma: no cover
