import sys
import click
from pathlib import Path

from star_handler.modules.processors.relion5_prep import Relion5PrepProcessor
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring
from star_handler.core.io import format_input_star

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(Relion5PrepProcessor.__doc__)

@click.command(
    name='process-relion5-prep',
    help=HELP,
    epilog=EPILOG
)
@click.option(
    '-i', '--list-star',
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help='Path to a STAR file listing multiple datasets to process in batch.'
)
@click.option(
    '-p', '--output-angpix',
    required=True,
    type=float,
    help='The final pixel size for the output particles.'
)
@click.option(
    "-o", "--output-dir",
    default="ribo_relion",
    show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Output master directory saving the relion5 processing folder."
)
@click.option(
    "-cp", "--combine-prefix",
    default="combine",
    show_default=True,
    help="Prefix for the output combined STAR files (e.g., combine.star)."
)
def main(list_star: str, output_angpix: float, output_dir: str, combine_prefix: str):
    try:
        logger.info(f"Starting batch processing with list file: {list_star}")
        star_data = format_input_star(list_star)
        
        data_block_key = 'star'
        if data_block_key not in star_data or star_data[data_block_key].empty:
            raise ValueError(f"Invalid list.star file: no '{data_block_key}' data block found.")

        processor = Relion5PrepProcessor(
            output_dir=output_dir,
            combine_prefix=combine_prefix
        )

        for index, row in star_data[data_block_key].iterrows():
            processor.process_dataset(row, output_angpix)
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
