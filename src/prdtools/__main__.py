try:
    import click
except ImportError:
    click = None

if click is not None:
    from .table import build
    from .designer import design

    @click.group()
    def cli():
        pass

    cli.add_command(build)
    cli.add_command(design)
else:
    from .table import main as cli

if __name__ == '__main__':
    cli()
