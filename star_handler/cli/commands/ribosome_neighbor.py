import sys
import click

from star_handler.modules.comparers.ribosome_neighbor import RibosomeNeighborComparer
from star_handler.utils.config import RibosomeNeighborConfig
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(RibosomeNeighborComparer.__doc__)

@click.command(
    name='compare-ribo-polysome',
    help=HELP,
    epilog=EPILOG
)
@click.option(
    '-f', '--star-file',
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help='Path to main ribosome STAR file.'
)
@click.option(
    "-en", "--entry-star",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=True,
    help="STAR file containing entry site coordinates"
)
@click.option(
    "-ex", "--exit-star",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=True,
    help="STAR file containing exit site coordinates"
)
@click.option(
    "-r", "--search-radius",
    type=float,
    default=RibosomeNeighborConfig().search_radius,
    show_default=True,
    help="Maximum neighbor search radius in Angstroms"
)
@click.option(
    "-b", "--bin-size",
    type=float,
    default=RibosomeNeighborConfig().bin_size,
    show_default=True,
    help="Size of distance histogram bins in Angstroms"
)
def main(star_file: str, entry_star: str, exit_star: str, search_radius: float, bin_size: float):
    try:
        analyzer = RibosomeNeighborComparer(
            star_file,
            entry_star,
            exit_star,
            search_radius=search_radius,
            bin_size=bin_size
        )
        analyzer.process()
        logger.info("Analysis complete!")
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
