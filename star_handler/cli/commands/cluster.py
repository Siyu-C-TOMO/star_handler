import sys
import click

from star_handler.modules.analyzers.cluster import ClusterAnalyzer
from star_handler.utils.config import ClusterConfig
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(ClusterAnalyzer.__doc__)

@click.command(
    name='analyze-cluster',
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
    "-t", "--threshold",
    type=float,
    default=ClusterConfig().threshold,
    show_default=True,
    help="Distance threshold in Angstroms"
)
@click.option(
    "-s", "--min-size",
    type=int,
    default=ClusterConfig().min_cluster_size,
    show_default=True,
    help="Minimum cluster size"
)
def main(star_file: str, threshold: float, min_size: int):
    try:
        analyzer = ClusterAnalyzer(
            star_file,
            threshold=threshold,
            min_cluster_size=min_size
        )
        analyzer.process()
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
