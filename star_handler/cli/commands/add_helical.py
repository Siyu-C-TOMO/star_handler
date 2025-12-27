import sys
import click

from star_handler.modules.processors.add_helical import AddHelByRefProcessor
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(AddHelByRefProcessor.__doc__)

@click.command(
    name='process-add-helical',
    help=HELP,
    epilog=EPILOG
)
@click.option(
    '-f', '--star-file',
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help='Path to the input STAR file.'
)
@click.option(
    "-r", "--star-ref",
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Reference STAR file"
)
@click.option(
    "-o", "--output-dir",
    default="modified",
    show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Output directory"
)
def main(star_file: str, star_ref: str, output_dir: str):
    try:
        processor = AddHelByRefProcessor(
            star_file,
            star_ref,
            output_dir
        )
        output_path = processor.process()
        print(f"Modified STAR file saved to: {output_path}")
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
