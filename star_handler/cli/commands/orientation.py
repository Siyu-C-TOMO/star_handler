import sys
import click

from star_handler.analyzers.orientation import OrientationAnalyzer
from star_handler.utils.config import OrientationConfig
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(OrientationAnalyzer.__doc__)

@click.command(
    name='star-orientation',
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
    "-m", "--max-angle",
    type=float,
    default=OrientationConfig().max_angle,
    show_default=True,
    help="Maximum angle to consider"
)
@click.option(
    "-b", "--bin-width",
    type=float,
    default=OrientationConfig().bin_width,
    show_default=True,
    help="Width of angle bins"
)
def main(star_file: str, max_angle: float, bin_width: float):
    try:
        analyzer = OrientationAnalyzer(
            star_file,
            max_angle=max_angle,
            bin_width=bin_width
        )
        analyzer.process()
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
