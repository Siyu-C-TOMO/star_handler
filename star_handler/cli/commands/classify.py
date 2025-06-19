import sys
from pathlib import Path
import click

from star_handler.core.selection import classify_star
from star_handler.utils.logger import setup_logger

logger = setup_logger(__name__)

HELP = "Classify particles in RELION STAR file based on metadata tag."
EPILOG = """
[WORKFLOW]
1. Read STAR file
2. Extract unique values from specified tag
3. Create classified sub-files

[PARAMETERS]
args : Optional[argparse.Namespace]
    Command line arguments:
    - star_file: Path to RELION STAR file
    - tag: Metadata tag for classification
    - partial_match: Number of parts to match
    - output_dir: Output directory

[OUTPUT]
- Multiple STAR files in specified output directory
- One file per unique tag value

[EXAMPLE]
Basic usage (classify by micrograph):
    $ star-handler star-classify -f particles.star
Custom tag and partial matching:
    $ star-handler star-classify -f particles.star -t rlnClassNumber -p 2
"""

@click.command(
    name='process-classify-by-tomo',
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
    "-t", "--tag",
    default="rlnMicrographName",
    show_default=True,
    help="Metadata tag for classification"
)
@click.option(
    "-p", "--partial-match",
    type=int,
    default=-1,
    show_default=True,
    help="Number of parts to match in tag value (-1 for full match)"
)
@click.option(
    "-o", "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Output directory (defaults to 'sub_folder')"
)
def main(star_file: Path, tag: str, partial_match: int, output_dir: Path):
    try:
        sub_files = classify_star(
            star_file,
            tag=tag,
            partial_match=partial_match,
            output_dir=output_dir
        )
        logger.info(f"Created {len(sub_files)} classified files")
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
