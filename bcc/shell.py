# shell completion

import os
import os.path
import sys

import click


def _shell_completion(ctx, option, shell):
    """output shell completion code"""

    if shell is None:
        return
    elif shell == "[auto]":
        if "SHELL" in os.environ:
            shell = os.path.basename(os.environ["SHELL"])
        elif "ZSH_VERSION" in os.environ:
            shell = "zsh"

    if shell not in ["bash", "zsh"]:
        raise RuntimeError("cannot determine shell")

    cli = os.path.basename(ctx.command_path)

    if shell == "bash":
        click.echo(f"Writing file ~/.{cli}-complete.bash...")
        os.system(f"_{cli.upper()}_COMPLETE=bash_source {cli} >~/.{cli}-complete.bash")
        click.echo("Source this file from ~/.bashrc")
        click.echo(f"ex: . ~/.{cli}-complete.bash")

    elif shell == "zsh":
        click.echo(f"Writing file ~/.{cli}-complete.zsh...")
        os.system(f"_{cli.upper()}_COMPLETE=zsh_source {cli} >~/.{cli}-complete.zsh")
        click.echo("Source this file from ~/.zshrc")
        click.echo(f"ex: . ~/.{cli}-complete.zsh")

    sys.exit(0)
