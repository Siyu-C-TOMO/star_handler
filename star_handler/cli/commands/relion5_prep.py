import sys
import click

from star_handler.modules.processors.relion5_prep import Relion5PrepProcessor
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(Relion5PrepProcessor.__doc__)

@click.command(
    name='process-relion5-prep',
    help=HELP,
    epilog=EPILOG
)
@click.option(
    '-p', '--prefix',
    required=True,
    help='Prefix to add to tomogram names and optics group.'
)
@click.option(
    '-i', '--input-dir',
    default='.',
    show_default=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Directory containing the input STAR files.'
)
@click.option(
    '-psd', '--particle-series-dir',
    default='particleseries',
    show_default=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Path to the particle series directory to be renamed.'
)
@click.option(
    "-o", "--output-dir",
    default=".",
    show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Output directory for combined files and renamed folder."
)
@click.option(
    "-cp", "--combine-prefix",
    default="combine",
    show_default=True,
    help="Prefix for the output combined STAR files (e.g., combine.star)."
)
def main(prefix: str, input_dir: str, particle_series_dir: str, output_dir: str, combine_prefix: str):
    try:
        processor = Relion5PrepProcessor(
            prefix=prefix,
            input_dir=input_dir,
            particle_series_dir=particle_series_dir,
            output_dir=output_dir,
            combine_prefix=combine_prefix
        )
        processor.process()
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
