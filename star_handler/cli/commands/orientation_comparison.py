import sys
import click

from star_handler.modules.comparers.orientation_comparer import OrientationComparer
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(OrientationComparer.__doc__)

@click.command(
    name='compare-orientation',
    help=HELP,
    epilog=EPILOG
)
@click.option(
    "--env-star",
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to the 'environment' STAR file"
)
@click.option(
    "--mem-star",
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to the 'membrane' STAR file"
)
@click.option(
    "-o", "--output-dir",
    default="orientation_comparison",
    show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Output directory for results"
)
def main(env_star: str, mem_star: str, output_dir: str):
    try:
        comparer = OrientationComparer(
            env_star=env_star,
            membrane_star=mem_star,
            output_dir=output_dir
        )
        comparer.compare()
        print(f"Orientation comparison complete. Results saved in {output_dir}")
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
