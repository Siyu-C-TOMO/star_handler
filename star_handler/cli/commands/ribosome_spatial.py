import sys
import click

from star_handler.modules.analyzers.ribosome_spatial import RibosomeSpatialAnalyzer
from star_handler.utils.config import (
    RadialConfig,
    ClusterConfig,
    OrientationConfig,
)
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring(RibosomeSpatialAnalyzer.__doc__)

@click.command(
    name='analyze-ribo-spatial',
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
    "--radial-bin-size",
    type=float,
    default=RadialConfig().bin_size,
    show_default=True,
    help="Size of radial distance bins in Angstroms"
)
@click.option(
    "--radial-max-distance",
    type=float,
    default=RadialConfig().max_distance,
    show_default=True,
    help="Maximum radial distance in Angstroms"
)
@click.option(
    "--cluster-threshold",
    type=float,
    default=ClusterConfig().threshold,
    show_default=True,
    help="Distance threshold for clustering in Angstroms"
)
@click.option(
    "--min-cluster-size",
    type=int,
    default=ClusterConfig().min_cluster_size,
    show_default=True,
    help="Minimum number of particles per cluster"
)
@click.option(
    "--angle-bin-width",
    type=float,
    default=OrientationConfig().bin_width,
    show_default=True,
    help="Width of angle bins in degrees"
)
@click.option(
    "--output-dir",
    type=str,
    default="analysis",
    show_default=True,
    help="Base output directory"
)
def main(star_file, radial_bin_size, radial_max_distance, cluster_threshold, min_cluster_size, angle_bin_width, output_dir):
    try:        
        logger.info("Starting ribosome spatial analysis")
        
        configs = {
            'radial': {'bin_size': radial_bin_size, 'max_distance': radial_max_distance},
            'cluster': {'threshold': cluster_threshold, 'min_cluster_size': min_cluster_size},
            'orientation': {'bin_width': angle_bin_width}
        }

        analyzer = RibosomeSpatialAnalyzer(
            star_file,
            output_dir=output_dir,
            configs=configs
        )
        analyzer.run_analysis()
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
