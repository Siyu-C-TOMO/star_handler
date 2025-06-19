from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

from star_handler.analyzers.base import BaseAnalyzer, AnalysisError
from ..core.io import format_input_star
from star_handler.utils.plot import plot_histogram
from star_handler.utils.config import RibosomeNeighborConfig

class RibosomeNeighborAnalyzer(BaseAnalyzer):
    """
    Analyze spatial relationships between neighboring ribosomes.
    
    [WORKFLOW]
    1. Read and process input STAR files:
       - Main ribosome positions
       - Entry site coordinates
       - Exit site coordinates
    2. For each tomogram:
       - Find neighbors within search radius
       - Calculate minimum site-to-site distances
    3. Generate statistics and visualizations

    [PARAMETERS]
    star_file : str
        Path to main ribosome STAR file
    entry_star : str
        Path to entry site STAR file
    exit_star : str
        Path to exit site STAR file
    search_radius : float, optional
        Maximum distance for considering neighbors
    bin_size : float, optional
        Size of distance histogram bins

    [OUTPUT]
    - Neighbor pairs and minimum site distances for each tomogram
    - Distance distribution histograms
    - Comprehensive statistics report

    [EXAMPLE]
    Basic usage:
        $ star-handler ribosome-neighbor -f ribosomes.star -en entry.star -ex exit.star

    Custom search radius:
        $ star-handler ribosome-neighbor -f ribosomes.star -en entry.star -ex exit.star -r 600
    """
    
    ANALYSIS_TYPE = "ribosome_neighbor"
    CONFIG_CLASS = RibosomeNeighborConfig
    
    def __init__(self,
                 star_file: str,
                 entry_star: str,
                 exit_star: str,
                 **config_params) -> None:
        """Initialize analyzer with input files and configuration.
        
        [PARAMETERS]
        star_file : str
            Path to main STAR file
        entry_star : str
            Path to entry site STAR file 
        exit_star : str
            Path to exit site STAR file
        **config_params
            Configuration parameters to override defaults
        """
        super().__init__(star_file, **config_params)
        
        self.entry_star = Path(entry_star)
        self.exit_star = Path(exit_star)
        
        if not self.entry_star.exists():
            raise FileNotFoundError(f"Entry site STAR file not found: {entry_star}")
        if not self.exit_star.exists():
            raise FileNotFoundError(f"Exit site STAR file not found: {exit_star}")
            
        
    def prepare_star_data(self) -> Tuple[Dict[str, pd.DataFrame], List[Path]]:
        """Process input STAR files and prepare for analysis.
        
        Extends base method to handle entry/exit site files.
        
        [WORKFLOW]
        1. Process main STAR file using parent method
        2. Process entry/exit site files using same scaling
        
        [OUTPUT]
        Tuple[Dict[str, pd.DataFrame], List[Path]]:
            - Processed STAR data
            - Paths to sub-files
        """
        try:
            star_data, sub_files = super().prepare_star_data()
            
            self.logger.info('Processing entry/exit site files')            
            _ , _ = super().prepare_star_data(
                input_file=self.entry_star,
                output_file_name='entry_processed.star',
                sub_dir_name='entry_sub_files'
            )
            _, _ = super().prepare_star_data(
                input_file=self.exit_star,
                output_file_name='exit_processed.star',
                sub_dir_name='exit_sub_files'
            )
            
            return star_data, sub_files
            
        except Exception as e:
            raise AnalysisError(f"Failed to prepare STAR data: {str(e)}")
            
    def _analyze(self,
                data: pd.DataFrame,
                coords: np.ndarray,
                dist_matrix: np.ndarray) -> Dict[str, Any]:
        """Analyze neighbors and calculate site distances.
        
        [WORKFLOW]
        1. Find neighbor pairs within search radius
        2. Get corresponding entry/exit coordinates 
        3. Calculate site-to-site distances
        
        [PARAMETERS]
        data : pd.DataFrame
            Particle data
        coords : np.ndarray
            Coordinate array
        dist_matrix : np.ndarray
            Distance matrix
            
        [OUTPUT]
        Dict[str, Any]:
            Analysis results including neighbor pairs and distances
        """
        neighbors = np.argwhere(np.triu(
            (dist_matrix <= self.config.search_radius) & 
            (dist_matrix > 0)  # Exclude self-pairs
        ))
        
        if len(neighbors) == 0:
            self.logger.warning("No neighbors found within search radius")
            return {
                'neighbor_pairs': [],
                'site_distances': [],
                'statistics': {
                    'n_pairs': 0,
                    'mean_distance': 0,
                    'min_distance': 0,
                    'max_distance': 0
                }
            }
            
        tomogram = Path(data['rlnMicrographName'].iloc[0]).stem
        entry_path = self.config.output_dir / 'entry_sub_files' / f"{tomogram}.star"
        exit_path = self.config.output_dir / 'exit_sub_files' / f"{tomogram}.star"
        
        tomogram_entry_data = format_input_star(entry_path)['particles']
        tomogram_exit_data = format_input_star(exit_path)['particles']
        
        particle_ids = data['rlnImageName']
        entry_coords = {}
        exit_coords = {}        
        for idx, full_name in enumerate(particle_ids):            
            entry_matches = tomogram_entry_data[
                tomogram_entry_data['rlnImageOriginalName'] == full_name
            ]
            if len(entry_matches) == 0:
                self.logger.warning(f"No entry site found for particle {full_name}")
                continue
            elif len(entry_matches) > 1:
                self.logger.warning(f"Multiple entry sites found for particle {full_name}")
                continue
                
            exit_matches = tomogram_exit_data[
                tomogram_exit_data['rlnImageOriginalName'] == full_name
            ]
            if len(exit_matches) == 0:
                self.logger.warning(f"No exit site found for particle {full_name}")
                continue
            elif len(exit_matches) > 1:
                self.logger.warning(f"Multiple exit sites found for particle {full_name}")
                continue
                
            entry_coords[idx] = entry_matches[['rlnCoordinateX', 'rlnCoordinateY', 'rlnCoordinateZ']].values[0]
            exit_coords[idx] = exit_matches[['rlnCoordinateX', 'rlnCoordinateY', 'rlnCoordinateZ']].values[0]
            
        site_distances = []
        valid_pairs = []
        
        for i, j in neighbors:
            if i not in entry_coords or j not in entry_coords:
                continue
                
            pair_dists = np.linalg.norm(
                np.array([
                    entry_coords[i] - exit_coords[j],
                    exit_coords[i] - entry_coords[j]
                ]), 
                axis=1
            )
            site_distances.append(np.min(pair_dists))
            valid_pairs.append((i, j))
            
        if not site_distances:
            self.logger.warning("No valid site distances found")
            return {
                'neighbor_pairs': [],
                'site_distances': [],
                'statistics': {
                    'n_pairs': 0,
                    'mean_distance': 0,
                    'min_distance': 0,
                    'max_distance': 0
                }
            }
            
        site_distances = np.array(site_distances)
        
        statistics = {
            'n_pairs': len(valid_pairs),
            'mean_distance': np.mean(site_distances),
            'std_distance': np.std(site_distances),
            'min_distance': np.min(site_distances),
            'max_distance': np.max(site_distances)
        }
        
        return {
            'neighbor_pairs': valid_pairs,
            'site_distances': site_distances,
            'statistics': statistics
        }
        
    def _save_tomogram_results(self,
                             tomogram: str,
                             results: Dict[str, Any]) -> None:
        """Save analysis results for a tomogram.
        
        [WORKFLOW]
        1. Save neighbor pairs and distances
        2. Create distance histogram
        
        [PARAMETERS]
        tomogram : str
            Tomogram identifier
        results : Dict[str, Any]
            Analysis results to save
        """
        if not results['neighbor_pairs']:
            return
            
        # Save pair data
        pairs_df = pd.DataFrame(
            results['neighbor_pairs'],
            columns=['Particle1', 'Particle2']
        )
        pairs_df['Distance'] = results['site_distances']
        
        pairs_file = self.output_dirs['data'] / f"{tomogram}_pairs.txt"
        pairs_df.to_csv(pairs_file, sep='\t', index=False)
        
        # Create histogram
        plot_histogram(
            results['site_distances'],
            str(self.output_dirs['plots'] / f"{tomogram}_distances"),
            xlabel='Minimum Site-to-site Distance (Å)',
            ylabel='Count',
            plot_type='distance'
        )
        
    def _combine_results(self,
                        results: List[Tuple[str, Dict[str, Any]]]
                        ) -> Dict[str, Any]:
        """Combine results from all tomograms.
        
        [WORKFLOW]
        1. Collect all distances
        2. Calculate overall statistics
        3. Generate combined plots
        
        [PARAMETERS]
        results : List[Tuple[str, Dict[str, Any]]]
            Results from each tomogram
            
        [OUTPUT]
        Dict[str, Any]:
            Combined statistics and data
        """
        all_distances = []
        tomogram_stats = []
        
        for tomogram, result in results:
            site_distances = np.asarray(result['site_distances'])
            if len(site_distances) > 0:
                all_distances.extend(site_distances)
                result['statistics']['tomogram'] = tomogram
                tomogram_stats.append(result['statistics'])
                
        if not all_distances:
            self.logger.warning("No distances found in any tomogram")
            return {
                'distances': np.array([]),
                'statistics': pd.DataFrame(),
                'overall_stats': {
                    'total_pairs': 0,
                    'mean_distance': 0,
                    'std_distance': 0
                }
            }
            
        all_distances = np.array(all_distances)
        stats_df = pd.DataFrame(tomogram_stats)
        
        stats_file = self.output_dirs['combined'] / 'statistics.txt'
        stats_df.to_csv(stats_file, sep='\t', index=False)
        
        plot_histogram(
            all_distances,
            str(self.output_dirs['combined'] / 'distance_distribution'),
            xlabel='Minimum Site-to-site Distance (Å)',
            ylabel='Count',
            plot_type='distance'
        )
        
        overall_stats = {
            'total_pairs': len(all_distances),
            'mean_distance': np.mean(all_distances),
            'std_distance': np.std(all_distances),
            'min_distance': np.min(all_distances),
            'max_distance': np.max(all_distances)
        }
        
        return {
            'distances': all_distances,
            'statistics': stats_df,
            'overall_stats': overall_stats
        }
        
    def _generate_report(self, results: Dict[str, Any]) -> None:
        """Generate analysis report.
        
        [WORKFLOW]
        1. Calculate overall statistics
        2. Write detailed report
        
        [PARAMETERS]
        results : Dict[str, Any]
            Combined analysis results
        """
        report_file = self.config.output_dir / 'neighbor_analysis_report.txt'
        
        with open(report_file, 'w') as f:
            self._write_report_section(f, "Ribosome Neighbor Analysis", {
                "Search radius": f"{self.config.search_radius} Å",
                "Bin size": f"{self.config.bin_size} Å",
                "Main STAR file": str(self.star_file),
                "Entry site file": str(self.entry_star),
                "Exit site file": str(self.exit_star)
            })
            
            if len(results['distances']) > 0:
                stats = results['overall_stats']
                stats_df = results['statistics']
                
                self._write_report_section(f, "Overall Statistics", {
                    "Total tomograms": len(stats_df),
                    "Total neighbor pairs": stats['total_pairs'],
                    "Mean min site distance": f"{stats['mean_distance']:.1f} ± {stats['std_distance']:.1f} Å",
                    "Distance range": f"{stats['min_distance']:.1f} - {stats['max_distance']:.1f} Å"
                })
                
                hist, bins = np.histogram(
                    results['distances'],
                    bins=np.arange(
                        0,
                        stats['max_distance'] + self.config.bin_size,
                        self.config.bin_size
                    )
                )
                
                dist_dist = {
                    f"{bins[i]:.0f}-{bins[i+1]:.0f} Å": count
                    for i, count in enumerate(hist)
                    if count > 0
                }
                
                self._write_report_section(f, "Distance Distribution", dist_dist)
                
            else:
                self._write_report_section(f, "Results", {
                    "Status": "No valid neighbors found"
                })
                
        self.logger.info(f"Analysis report saved to {report_file}")
