import sys
import click

from star_handler.modules.processors.template_match import TemplateMatch3DProcessor
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(TemplateMatch3DProcessor.__doc__)

@click.command(
    name='process-3DTM2relion',
    help=HELP,
    epilog=EPILOG
)
@click.option(
    "-d", "--dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    default='.',
    show_default=True,
    help="Working directory containing star files"
)
def main(directory: str):
    try:
        processor = TemplateMatch3DProcessor(directory)
        processor.process()
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
