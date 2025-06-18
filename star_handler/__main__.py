import click
import importlib
from pathlib import Path
from textwrap import dedent

_commands = {}
_commands_dir = Path(__file__).parent / "cli" / "commands"

def _load_commands():
    if _commands:
        return
    for fn in _commands_dir.glob("*.py"):
        if fn.name == "__init__.py":
            continue
        mod = importlib.import_module(f"star_handler.cli.commands.{fn.stem}")
        if hasattr(mod, "main") and isinstance(mod.main, click.Command):
            _commands[mod.main.name] = mod.main

class DynamicCommands(click.MultiCommand):
    def list_commands(self, ctx):
        _load_commands()
        return sorted(_commands.keys())

    def get_command(self, ctx, name):
        _load_commands()
        cmd = _commands.get(name)
        if cmd and hasattr(cmd, "epilog"):
            def raw_format_epilog(this, ctx, formatter):
                if this.epilog:
                    formatter.write_paragraph()
                    raw = dedent(this.epilog).lstrip("\n")
                    old_indent = formatter.current_indent
                    formatter.current_indent = 0
                    formatter.write(raw + "\n")
                    formatter.current_indent = old_indent

            cmd.format_epilog = raw_format_epilog.__get__(cmd, type(cmd))
        return cmd

@click.group(cls=DynamicCommands)
def cli():
    """
    A comprehensive toolkit for analyzing RELION STAR files.
    """
    pass

if __name__ == "__main__":
    cli()
