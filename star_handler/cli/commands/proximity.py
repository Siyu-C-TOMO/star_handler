import sys
import click

from star_handler.analyzers.proximity_comparer import ProximityComparer
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(ProximityComparer.__doc__)

@click.command(
    name='star-compare-proximity',
    help=HELP,
    epilog=EPILOG
)
@click.option(
    "--star-a",
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    help="Path to the primary STAR file (Set A)."
)
@click.option(
    "--star-b",
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    help="Path to the secondary STAR file to compare against (Set B)."
)
@click.option(
    "--threshold",
    required=True,
    type=float,
    help="Distance threshold in pixels to define a neighbor."
)
@click.option(
    "-o", "--output-dir",
    default="proximity_comparison",
    show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Output directory for results."
)
def main(star_a: str, star_b: str, threshold: float, output_dir: str):
    """
    Command-line interface for running the proximity analysis.
    """
    try:
        logger.info("Starting proximity comparison...")
        comparer = ProximityComparer(
            star_file_a=star_a,
            star_file_b=star_b,
            threshold=threshold,
            output_dir=output_dir
        )
        results = comparer.compare()
        
        percentage = results.get('percentage', 0)
        logger.info(f"Analysis complete. {percentage:.2f}% of particles in Set A have a neighbor in Set B.")
        print(f"Proximity comparison complete. Results saved in '{output_dir}'")
        
    except Exception as e:
        logger.error(f"An error occurred during proximity comparison: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
