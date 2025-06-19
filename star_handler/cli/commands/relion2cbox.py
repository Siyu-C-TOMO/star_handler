import sys
import click

from star_handler.modules.processors.relion2cbox import Relion2CboxProcessor
from star_handler.utils.config import Relion2CboxConfig
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(Relion2CboxProcessor.__doc__)

@click.command(
    name='process-relion2cryolo',
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
    "-b", "--bin-factor",
    type=int,
    default=Relion2CboxConfig().bin_factor,
    show_default=True,
    help="Unbinning factor for coordinates"
)
def main(star_file: str, bin_factor: int):
    try:
        processor = Relion2CboxProcessor(
            star_file,
            bin_factor
        )
        processor.process()
        print("Processing complete!")
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
