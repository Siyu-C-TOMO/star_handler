import sys
from pathlib import Path
import click

from star_handler.core.selection import split_star_by_threshold
from star_handler.utils.logger import setup_logger

logger = setup_logger(__name__)

HELP = "Split STAR file based on a column's value threshold."
EPILOG = """
[WORKFLOW]
1. Read STAR file
2. Split particles based on one or more thresholds
3. Create new STAR files for each value range

[PARAMETERS]
args : Optional[argparse.Namespace]
    Command line arguments:
    - star_file: Path to RELION STAR file
    - tag: Metadata tag to apply threshold on
    - thresholds: One or more threshold values
    - output_dir: Output directory

[OUTPUT]
- Multiple STAR files in specified output directory
- Files are named based on the ranges (e.g., le_45.0, gt_45.0)

[EXAMPLE]
Split by a single threshold on rlnAngleTilt:
    $ star-handler star-split-by-threshold -f particles.star -t rlnAngleTilt -th 45.0

Split into multiple ranges on rlnDefocusU:
    $ star-handler star-split-by-threshold -f particles.star -t rlnDefocusU -th 20000 30000
"""

@click.command(
    name='process-split-by-thres',
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
    required=True,
    help="Metadata tag to apply threshold on (e.g., rlnAngleTilt)"
)
@click.option(
    "-th", "--thresholds",
    type=float,
    multiple=True,
    required=True,
    help="One or more threshold values"
)
@click.option(
    "-o", "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Output directory (defaults to 'threshold_split' in star file's parent dir)"
)
def main(star_file: Path, tag: str, thresholds: tuple[float, ...], output_dir: Path):
    try:
        thresholds_to_pass = list(thresholds)
        
        output_files = split_star_by_threshold(
            star_file_path=star_file,
            tag=tag,
            thresholds=thresholds_to_pass,
            output_dir=output_dir
        )
        logger.info(f"Successfully created {len(output_files)} split files.")
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
