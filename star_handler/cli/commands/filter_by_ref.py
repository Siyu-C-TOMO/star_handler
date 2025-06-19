import sys
import click

from star_handler.processors.filter_by_ref import FilterByRefProcessor
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(FilterByRefProcessor.__doc__)

@click.command(
    name='process-filter-by-ref',
    help=HELP,
    epilog=EPILOG
)
@click.option(
    '-f', '--star-file',
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help='Path to STAR file to be filtered.'
)
@click.option(
    "-r", "--ref-star",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=True,
    help="Path to reference STAR file"
)
@click.option(
    "-o", "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Output directory for filtered files"
)
def main(star_file: str, ref_star: str, output_dir: str):
    try:
        processor = FilterByRefProcessor(
            star_file,
            ref_star,
            output_dir=output_dir
        )
        output_path = processor.process()
        logger.info(f"Successfully filtered particles. Output saved to: {output_path}")
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
