import sys
from pathlib import Path
import click

from star_handler.modules.analyzers.tabulation_class import ClassDistribution
from star_handler.utils.config import ClassDistributionConfig
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(ClassDistribution.__doc__)

@click.command(
    name='analyze-class-distribution',
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
    "-g", "--group-column",
    default=ClassDistributionConfig().group_column,
    show_default=True,
    help="Column defining dataset groups"
)
@click.option(
    "-o", "--output",
    default=ClassDistributionConfig().output_file,
    show_default=True,
    help="Output filename for distribution table"
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Output directory for results"
)
def main(star_file: str, group_column: str, output: str, output_dir: Path):
    try:
        analyzer = ClassDistribution(
            star_file,
            group_column=group_column,
            output_file=output
        )
        
        distribution, stats = analyzer.analyze()
        analyzer.save_results(
            distribution,
            stats,
            output_dir=Path(output_dir) if output_dir else None
        )
        
        logger.info("\nClassification Analysis Summary:")
        logger.info(f"Total particles: {stats['total_particles']}")
        logger.info(f"Number of classes: {stats['n_classes']}")
        logger.info(f"Largest class: {stats['largest_class']} "
                   f"({stats['largest_class_percentage']:.1f}%)")
        if output_dir:
            logger.info(f"\nResults saved to: {Path(output_dir).absolute()}")
        
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()
