import sys
import click
from pathlib import Path

from star_handler.modules.processors.m_combine import MCombineProcessor
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(MCombineProcessor.__doc__)

@click.command(
    name='process-m-combine',
    help=HELP,
    epilog=EPILOG
)
@click.option(
    '-i', '--star-file',
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help='Path to the RELION 5 star file containing optics groups to process.'
)
@click.option(
    '-o', '--output-dir',
    default='ribo_m',
    show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help='Output master directory for the M processing.'
)
@click.option(
    '--skip-prepare',
    is_flag=True,
    help='Skip file preparation and directly run M-pipeline with existing source files.'
)
def main(star_file: str, output_dir: str, skip_prepare: bool):
    try:
        logger.info(f"Initializing M-Combine processor for star file: {star_file}")
        
        job_dir = str(Path(star_file).parent)
        
        m_params = {
            "job_dir": job_dir
        }

        processor = MCombineProcessor(
            star_file=star_file,
            output_dir=output_dir,
            m_parameters=m_params,
            skip_prepare=skip_prepare
        )
        processor.run()
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
