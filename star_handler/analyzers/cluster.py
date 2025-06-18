"""
Cluster analysis for particles.

Identifies and analyzes spatial clusters based on distance thresholds.
Uses efficient algorithms from matrix_math module for clustering.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Union
import numpy as np
import pandas as pd

from star_handler.analyzers.base import BaseAnalyzer
from star_handler.core.matrix_math import find_particle_clusters
from star_handler.utils.plot import plot_histogram
from star_handler.utils.config import ClusterConfig

class ClusterAnalyzer(BaseAnalyzer):
    """
    Analyze particle clusters in RELION STAR file.
    
    [WORKFLOW]
    1. Read particle coordinates from STAR file
    2. Identify particle clusters using distance threshold
    3. Filter clusters by minimum size
    4. Generate cluster statistics and visualizations

    [PARAMETERS]
    star_file : str
        Path to input STAR file
    output_dir : Union[str, Path]
        Base output directory
    threshold : Optional[float]
        Distance threshold for clustering (Å)
    min_cluster_size : Optional[int]
        Minimum particles per cluster

    [OUTPUT]
    - clusters.pdf: Cluster visualization plot
    - cluster_stats.csv: Cluster statistics

    [EXAMPLE]
    Find clusters with 380Å threshold and minimum 2 particles:
        $ star-handler star-cluster -f particles.star -t 380 -s 2
    """
    
    ANALYSIS_TYPE = "cluster"
    CONFIG_CLASS = ClusterConfig
    
    CLUSTER_STATS = {
        'size': {
            'key': 'size_distribution',
            'label': 'Cluster Size',
            'ylabel': 'Count',
            'plot_type': 'cluster'
        }
    }
    
    def __init__(self,
                 star_file: str,
                 output_dir: Union[str, Path] = 'analysis',
                 threshold: float = None,
                 min_cluster_size: int = None) -> None:
        """Initialize ClusterAnalyzer.
        
        [PARAMETERS]
        star_file : str
            Path to input STAR file
        output_dir : Union[str, Path]
            Base output directory, defaults to 'analysis'
        threshold : Optional[float]
            Distance threshold for clustering (Å)
        min_cluster_size : Optional[int]
            Minimum particles per cluster
            
        [EXAMPLE]
        >>> analyzer = ClusterAnalyzer("particles.star", threshold=380)
        """
        super().__init__(
            star_file,
            output_dir=output_dir,
            threshold=threshold,
            min_cluster_size=min_cluster_size
        )
        
    def _analyze(self,
                data: pd.DataFrame,
                coords: np.ndarray,
                dist_matrix: np.ndarray) -> Dict[str, Any]:
        """Perform cluster analysis.
        
        [WORKFLOW]
        1. Build adjacency matrix from distance matrix
        2. Find clusters
        3. Calculate statistics
        
        [PARAMETERS]
        data : pd.DataFrame
            Particle data (for reference)
        coords : np.ndarray
            Coordinate array
        dist_matrix : np.ndarray
            Distance matrix
            
        [OUTPUT]
        Dict[str, Any]:
            'clusters': List of particle clusters
            'size_dist': Size distribution
            'statistics': Basic statistics
        """
        adjacency = dist_matrix <= self.config.threshold
        np.fill_diagonal(adjacency, False)  # Remove self-connections
        
        clusters, size_dist = find_particle_clusters(adjacency)
        
        filtered_clusters = [
            cluster for cluster in clusters
            if len(cluster) >= self.config.min_cluster_size
        ]
        
        if not filtered_clusters:
            self.logger.warning("No clusters found above minimum size")
            return {
                'clusters': [],
                'size_dist': {},
                'statistics': {
                    'n_clusters': 0,
                    'total_particles': 0,
                    'largest_size': 0,
                    'avg_size': 0
                }
            }
            
        cluster_sizes = [len(c) for c in filtered_clusters]
        
        statistics = {
            'n_clusters': len(filtered_clusters),
            'total_particles': sum(cluster_sizes),
            'largest_size': max(cluster_sizes),
            'avg_size': np.mean(cluster_sizes)
        }
        
        return {
            'clusters': filtered_clusters,
            'size_dist': size_dist,
            'statistics': statistics
        }
        
    def _save_tomogram_results(self,
                             tomogram: str,
                             results: Dict[str, Any]) -> None:
        """Save clustering results for a tomogram.
        
        [WORKFLOW]
        1. Save cluster assignments
        2. Save size distribution
        3. Create visualizations
        
        [PARAMETERS]
        tomogram : str
            Tomogram identifier
        results : Dict[str, Any]
            Analysis results with clusters and statistics
        """
        cluster_data = [{
            'Cluster': i+1,
            'Size': len(cluster),
            'Members': ', '.join(map(str, cluster))
        } for i, cluster in enumerate(results['clusters'])]
        self._save_data(cluster_data, f"{tomogram}_clusters")
        
        if results['size_dist']:
            size_data = []
            for size, count in results['size_dist'].items():
                if size >= self.config.min_cluster_size:
                    size_data.extend([size] * count)
                    
            if size_data:
                data_file = self._save_data(
                    {'Size': size_data},
                    f"{tomogram}_sizes"
                )
                plot_histogram(
                    np.array(size_data),
                    str(self.output_dirs['plots'] / f"{tomogram}_sizes"),
                    plot_type=self.CLUSTER_STATS['size']['plot_type'],
                    xlabel=self.CLUSTER_STATS['size']['label'],
                    ylabel=self.CLUSTER_STATS['size']['ylabel']
                )
        
    def _combine_results(self,
                        results: List[Tuple[str, Dict[str, Any]]]
                        ) -> Dict[str, Any]:
        """Combine clustering results from all tomograms.
        
        [WORKFLOW]
        1. Combine statistics
        2. Create overall distribution
        3. Generate summary plots
        
        [PARAMETERS]
        results : List[Tuple[str, Dict[str, Any]]]
            Results from each tomogram
            
        [OUTPUT]
        Dict[str, Any]:
            'combined_stats': Overall statistics
            'size_distribution': Combined distribution
        """
        all_stats = []
        all_sizes = []
        
        for tomogram, result in results:
            stats = result['statistics']
            stats['tomogram'] = tomogram
            all_stats.append(stats)
            
            for size, count in result['size_dist'].items():
                if size >= self.config.min_cluster_size:
                    all_sizes.extend([size] * count)
                    
        combined_stats = pd.DataFrame(all_stats)
        self._save_data(combined_stats, 'cluster_statistics', prefix='combined')
        
        if all_sizes:
            size_data = self._save_data(
                {'Size': all_sizes},
                'all_sizes',
                prefix='combined'
            )
            
            config = self.CLUSTER_STATS['size']
            plot_histogram(
                np.array(all_sizes),
                str(self.output_dirs['combined'] / 'size_distribution'),
                plot_type=config['plot_type'],
                xlabel=config['label'],
                ylabel=config['ylabel']
            )
            
        return {
            'combined_stats': combined_stats,
            'size_distribution': all_sizes
        }
        
    def _generate_report(self, results: Dict[str, Any]) -> None:
        """Generate clustering analysis report.
        
        [WORKFLOW]
        1. Calculate overall statistics
        2. Write detailed report
        
        [PARAMETERS]
        results : Dict[str, Any]
            Combined analysis results
        """
        stats = results['combined_stats']
        sizes = results['size_distribution']
        
        report_file = self.output_dir / 'cluster_report.txt'
        with open(report_file, 'w') as f:
            self._write_report_section(f, "Particle Cluster Analysis", {
                "Distance threshold": f"{self.config.threshold} Å",
                "Minimum cluster size": self.config.min_cluster_size
            })
            
            self._write_report_section(f, "Dataset Statistics", {
                "Number of tomograms": len(stats),
                "Total clusters": stats['n_clusters'].sum(),
                "Total clustered particles": stats['total_particles'].sum()
            })
            
            if sizes:
                self._write_report_section(f, "Cluster Statistics", {
                    "Average cluster size": f"{np.mean(sizes):.1f}",
                    "Largest cluster": f"{max(sizes)} particles",
                    "Size standard deviation": f"{np.std(sizes):.1f}"
                })
                
                size_dist = {f"{size} particles": f"{sizes.count(size)} clusters"
                           for size in sorted(set(sizes))}
                self._write_report_section(f, "Size Distribution", size_dist)
            
        self.logger.info(f"Analysis report saved to {report_file}")
