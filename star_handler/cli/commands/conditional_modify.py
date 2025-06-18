import sys
import click

from star_handler.processors.conditional_modify import ConditionalModifyProcessor
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(ConditionalModifyProcessor.__doc__)

@click.command(
    name='star-modify-conditional',
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
    "-c", "--condition",
    required=True,
    help="Value that must match in reference column"
)
@click.option(
    "-s", "--string",
    required=True,
    help="String to prepend if condition is met"
)
@click.option(
    "-r", "--column-ref",
    default="rlnOpticsGroup",
    show_default=True,
    help="Column to check for condition"
)
@click.option(
    "-m", "--column-to-modify",
    default="rlnMicrographName",
    show_default=True,
    help="Column to modify"
)
@click.option(
    "-o", "--output-dir",
    default="modified",
    show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Output directory"
)
def main(star_file: str, condition: str, string: str, column_ref: str, column_to_modify: str, output_dir: str):
    try:
        processor = ConditionalModifyProcessor(
            star_file,
            condition,
            string,
            column_ref,
            column_to_modify,
            output_dir
        )
        output_path = processor.process()
        print(f"Modified STAR file saved to: {output_path}")
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
