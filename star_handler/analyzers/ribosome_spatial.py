"""Comprehensive spatial analysis for ribosome particles.

Performs combined radial distribution, clustering, and orientation analyses 
while optimizing data preprocessing by sharing processed results between analyzers.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Union

from star_handler.analyzers import (
    RadialAnalyzer,
    ClusterAnalyzer,
    OrientationAnalyzer
)
from star_handler.utils.logger import setup_logger, log_execution

logger = setup_logger(__name__)

class RibosomeSpatialAnalyzer:
    """
    Analyze ribosome spatial distributions in RELION STAR file.
    
    [WORKFLOW]
    1. Process input data once and share between analyzers
    2. Execute radial distribution analysis
    3. Execute cluster analysis
    4. Execute orientation analysis
    5. Generate comprehensive report

    [PARAMETERS]
    star_file : str
        Path to input STAR file
    output_dir : Union[str, Path]
        Base output directory
    configs : Optional[Dict[str, Dict[str, Any]]]
        Configuration dictionary for each analyzer

    [OUTPUT]
    - Combined analysis report and individual analysis outputs
    - Efficiency improved by sharing processed data

    [EXAMPLE]
    Analyze ribosome spatial distributions with default parameters:
        $ star-handler ribosome-spatial -f ribosomes.star
    """
    
    def __init__(self, 
                 star_file: str,
                 output_dir: Union[str, Path] = 'analysis',
                 configs: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """Initialize analyzer with input file and configurations.
        
        [PARAMETERS]
        star_file : str
            Path to input STAR file
        output_dir : Union[str, Path]
            Base output directory, defaults to 'analysis'
        configs : Optional[Dict[str, Dict[str, Any]]]
            Configuration dictionary for each analyzer:
            {
                'radial': {...},
                'cluster': {...},
                'orientation': {...}
            }
        """
        self.star_file = Path(star_file)
        if not self.star_file.exists():
            raise FileNotFoundError(f"STAR file not found: {star_file}")
            
        self.output_dir = Path(output_dir)
        self.configs = configs or {}
        self.processed_star = None
        self.sub_files = None
        
        # Create RadialAnalyzer for file processing and utility methods
        self.processor = RadialAnalyzer(star_file, output_dir=self.output_dir)
        
    @log_execution(notify=True)
    def run_analysis(self) -> Dict[str, Any]:
        """Run complete spatial analysis.
        
        [WORKFLOW]
        1. Use RadialAnalyzer's prepare_star_data to process input
        2. Share processed data with each analyzer
        3. Generate analysis results
        
        [OUTPUT]
        Dict[str, Any]:
            Combined results from all analyses
        """
        self.processed_star, self.sub_files = self.processor.prepare_star_data()
        
        results = {}
        
        try:
            logger.info("Running radial distribution analysis")
            radial = RadialAnalyzer(
                str(self.star_file),
                output_dir=self.output_dir,
                **self.configs.get('radial', {})
            )
            radial.processed_star = self.processed_star
            radial.sub_files = self.sub_files
            results['radial'] = radial.process()
            
            logger.info("Running cluster analysis")
            cluster = ClusterAnalyzer(
                str(self.star_file),
                output_dir=self.output_dir,
                **self.configs.get('cluster', {})
            )
            cluster.processed_star = self.processed_star
            cluster.sub_files = self.sub_files
            results['cluster'] = cluster.process()
            
            logger.info("Running orientation analysis")
            orientation = OrientationAnalyzer(
                str(self.star_file),
                output_dir=self.output_dir,
                **self.configs.get('orientation', {})
            )
            orientation.processed_star = self.processed_star
            orientation.sub_files = self.sub_files
            results['orientation'] = orientation.process()
            
            self._generate_report(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise
            
    def _generate_report(self, results: Dict[str, Any]) -> None:
        """Generate comprehensive analysis report.
        
        Uses RadialAnalyzer's report section writing method for consistency.
        
        [PARAMETERS]
        results : Dict[str, Any]
            Results from all analyses
        """
        report_file = self.output_dir / 'report.txt'
        
        with open(report_file, 'w') as f:
            particles = self.processed_star['particles']
            self.processor._write_report_section(f, "Dataset Summary", {
                "Input file": str(self.star_file),
                "Total particles": len(particles),
                "Number of tomograms": len(particles['rlnMicrographName'].unique())
            })
            
            try:
                if 'radial' in results:
                    rad_stats = results['radial']['average']
                    try:
                        peak_dist = float(rad_stats['Distance'].iloc[rad_stats['g_r_mean'].idxmax()])
                        peak_height = float(rad_stats['g_r_mean'].max())
                        self.processor._write_report_section(f, "Radial Distribution Summary", {
                            "Peak g(r) at": f"{peak_dist:.1f} Å",
                            "Peak height": f"{peak_height:.2e}"
                        })
                    except Exception as e:
                        logger.warning(f"Failed to format radial distribution stats: {str(e)}")
                    
                if 'cluster' in results:
                    try:
                        cluster_stats = results['cluster']['combined_stats']
                        total_clusters = int(cluster_stats['n_clusters'].sum())
                        avg_size = float(cluster_stats['avg_size'].mean())
                        self.processor._write_report_section(f, "Cluster Analysis Summary", {
                            "Total clusters": total_clusters,
                            "Average cluster size": f"{avg_size:.1f} particles"
                        })
                    except Exception as e:
                        logger.warning(f"Failed to format cluster stats: {str(e)}")
                    
                if 'orientation' in results:
                    try:
                        orient_stats = results['orientation']['statistics']
                        self.processor._write_report_section(f, "Orientation Analysis Summary", {
                            "Mean angle": f"{float(orient_stats['mean_angle']):.1f}° ± {float(orient_stats['std_angle']):.1f}°",
                            "Median angle": f"{float(orient_stats['median_angle']):.1f}°"
                        })
                    except Exception as e:
                        logger.warning(f"Failed to format orientation stats: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to generate sections of report: {str(e)}")
                
            logger.info(f"Combined report saved to {report_file}")
