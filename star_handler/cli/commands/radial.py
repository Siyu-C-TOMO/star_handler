import sys
import click

from star_handler.modules.analyzers.radial import RadialAnalyzer
from star_handler.utils.config import RadialConfig
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(RadialAnalyzer.__doc__)

@click.command(
    name='analyze-radial',
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
    "-b", "--bin-size",
    type=float,
    default=RadialConfig().bin_size,
    show_default=True,
    help="Size of distance bins in Angstroms"
)
@click.option(
    "-m", "--max-distance",
    type=float,
    default=RadialConfig().max_distance,
    show_default=True,
    help="Maximum distance to consider"
)
@click.option(
    "--min-distance",
    type=float,
    default=RadialConfig().min_distance,
    show_default=True,
    help="Minimum distance to consider"
)
def main(star_file: str, bin_size: float, max_distance: float, min_distance: float):
    try:
        analyzer = RadialAnalyzer(
            star_file,
            bin_size=bin_size,
            min_distance=min_distance,
            max_distance=max_distance
        )
        analyzer.process()
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
