"""
Radial distribution analysis for particles.

Calculates g(r) to analyze spatial distributions of particles.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Union, Optional

import numpy as np
import pandas as pd

from star_handler.core.matrix_math import gr, local_density, distance_weighted
from star_handler.analyzers.base import BaseAnalyzer
from star_handler.utils.plot import plot_xy, plot_histogram
from star_handler.utils.config import RadialConfig

class RadialAnalyzer(BaseAnalyzer):
    """
    Analyze radial distribution of particles in RELION STAR file.
    
    [WORKFLOW]
    1. Read particle coordinates from STAR file
    2. Calculate pairwise distances between particles
    3. Generate radial distribution histogram
    4. Plot results and save to file

    [PARAMETERS]
    star_file : str
        Path to input STAR file
    output_dir : Union[str, Path]
        Base output directory
    bin_size : Optional[float]
        Size of distance bins in Angstroms
    min_distance : Optional[float]
        Minimum distance to consider
    max_distance : Optional[float]
        Maximum distance to consider

    [OUTPUT]
    - radial_dist.pdf: Radial distribution plot
    - radial_data.csv: Raw histogram data

    [EXAMPLE]
    Analyze particles with 50Å bins up to 8000Å:
        $ star-handler star-radial -f particles.star -b 50 -m 8000
    """
    
    ANALYSIS_TYPE = "radial"
    CONFIG_CLASS = RadialConfig
    
    DISTRIBUTIONS = {
        'rdf': {
            'key': 'g_r',
            'label': 'g(r)',
            'ylabel': 'g(r)'
        },
        'local_density': {
            'key': 'local_density',
            'label': 'Local Density',
            'ylabel': 'Local Density'
        },
        'distance_weighted': {
            'key': 'distance_weighted',
            'label': 'Distance Weighted Density',
            'ylabel': 'Distance Weighted Density'
        }
    }
    
    def __init__(self,
                 star_file: str,
                 output_dir: Union[str, Path] = 'analysis',
                 **kwargs) -> None:
        """Initialize RadialAnalyzer.
        
        [PARAMETERS]
        star_file : str
            Path to input STAR file
        output_dir : Union[str, Path]
            Base output directory, defaults to 'analysis'
        **kwargs : Any
            Additional configuration parameters (e.g., bin_size, min_distance, max_distance)
            
        [EXAMPLE]
        >>> analyzer = RadialAnalyzer("particles.star", bin_size=50)
        """
        super().__init__(star_file, output_dir=output_dir, **kwargs)
        
    def _create_bins(self) -> Tuple[np.ndarray, np.ndarray]:
        """Create distance bins based on configuration.
        
        [OUTPUT]
        Tuple[np.ndarray, np.ndarray]:
            - bins: Array of bin edges
            - bin_centers: Array of bin centers
        """
        bins = np.arange(
            0,
            self.config.max_distance + self.config.bin_size,
            self.config.bin_size
        )
        bin_centers = 0.5 * (bins[1:] + bins[:-1])
        return bins, bin_centers

    def _calculate_box_volume(self, coords: np.ndarray, distances: np.ndarray, n_particles: int) -> float:
        """Calculate a safe, non-zero box volume.
        
        [WORKFLOW]
        1. Calculate coordinate ranges
        2. Calculate box volume
        3. Fallback to mean distance if box volume is invalid
        
        [PARAMETERS]
        coords : np.ndarray
            Particle coordinates
        distances : np.ndarray
            Pairwise distances between particles
        n_particles : int
            Number of particles
            
        [OUTPUT]
        float:
            Calculated box volume, or fallback value if invalid
        """
        if n_particles < 2:
            return 1.0  

        coord_ranges = coords.max(axis=0) - coords.min(axis=0)
        coord_ranges = np.maximum(coord_ranges, 1.0)
        box_volume = np.prod(coord_ranges)
        
        if box_volume <= 0:
            self.logger.warning(f"Invalid box volume ({box_volume}). Using fallback calculation.")
            if len(distances) > 0:
                mean_nn_dist = np.mean(distances)
                box_volume = (mean_nn_dist ** 3) * n_particles
            else:
                box_volume = 1000.0
        
        return box_volume

    def _calculate_distributions(self, distances: np.ndarray, bins: np.ndarray, box_volume: float, n_particles: int) -> Dict[str, Any]:
        """Calculate all radial distributions.
        
        [WORKFLOW]
        1. Check if sufficient particles are available
        2. Calculate g(r) using shell volume normalization
        3. Calculate local density using expected pairs normalization
        4. Calculate distance weighted density using r² normalization
        5. Return all distributions in a dictionary
        
        [PARAMETERS]
        distances : np.ndarray
            Pairwise distances between particles
        bins : np.ndarray
            Distance bins for histogram
        box_volume : float
            Calculated box volume
        n_particles : int
            Number of particles
        
        [OUTPUT]
        Dict[str, Any]:
            Dictionary containing:
            - 'g_r': Radial distribution function g(r)
            - 'local_density': Local density distribution
            - 'distance_weighted': Distance weighted density distribution
            - 'insufficient_particles': Boolean flag if insufficient particles were found
        """
        if n_particles < 3:
            self.logger.warning(f"Insufficient particles ({n_particles}) for RDF analysis. Returning zero distributions.")
            zeros = np.zeros_like(0.5 * (bins[1:] + bins[:-1]))
            return {
                'g_r': zeros,
                'local_density': zeros,
                'distance_weighted': zeros,
                'insufficient_particles': True
            }

        return {
            'g_r': gr(distances, bins, box_volume, n_particles),
            'local_density': local_density(distances, bins, box_volume, n_particles),
            'distance_weighted': distance_weighted(distances, bins),
            'insufficient_particles': False
        }

    def _analyze(self,
                data: pd.DataFrame,
                coords: np.ndarray,
                dist_matrix: np.ndarray) -> Dict[str, Any]:
        """Calculate radial distribution function.
        
        [WORKFLOW]
        1. Prepare initial data (particle count, distances).
        2. Create distance bins.
        3. Calculate a safe box volume.
        4. Calculate all distributions.
        5. Combine results and apply distance mask.
        
        [PARAMETERS]
        data : pd.DataFrame
            Particle data (unused)
        coords : np.ndarray
            Coordinate array
        dist_matrix : np.ndarray
            Distance matrix
            
        [OUTPUT]
        Dict[str, Any]:
            Dictionary containing all analysis results.
        """
        n_particles = len(coords)
        distances = dist_matrix[np.triu_indices_from(dist_matrix, k=1)]

        bins, bin_centers = self._create_bins()
        box_volume = self._calculate_box_volume(coords, distances, n_particles)
        
        distributions = self._calculate_distributions(
            distances, bins, box_volume, n_particles
        )

        results = {
            'distances': bin_centers,
            'raw_distances': distances.tolist(),
            'particle_density': n_particles / box_volume if box_volume > 0 else 0.0,
            **distributions
        }

        mask = results['distances'] < self.config.min_distance
        for dist_config in self.DISTRIBUTIONS.values():
            key = dist_config['key']
            if key in results:
                results[key][mask] = 0
        
        return results
        
    def _save_tomogram_results(self,
                             tomogram: str,
                             results: Dict[str, Any]) -> None:
        """Save RDF results for a single tomogram.
        
        [WORKFLOW]
        1. Check if tomogram has sufficient particles
        2. Save each distribution type
        3. Create visualizations
        
        [PARAMETERS]
        tomogram : str
            Tomogram identifier
        results : Dict[str, Any]
            Analysis results with all normalization methods
        """
        if results.get('insufficient_particles', False):
            self.logger.info(f"Skipping result saving for {tomogram} (insufficient particles)")
            return
            
        for dist_type, config in self.DISTRIBUTIONS.items():
            data_file = self._save_data(
                {
                    'Distance': results['distances'],
                    config['key']: results[config['key']]
                },
                f"{tomogram}_{dist_type}"
            )
            
            plot_xy(
                str(data_file),
                str(self.output_dirs['plots'] / f"{tomogram}_{dist_type}.png"),
                xlabel='r (Å)',
                ylabel=config['ylabel']
            )
        
    def _combine_results(self,
                        results: List[Tuple[str, Dict[str, Any]]]
                        ) -> Dict[str, Any]:
        """Combine RDF data from all tomograms.
        
        [WORKFLOW]
        1. Collect all results
        2. Calculate average for all normalization methods
        3. Create combined visualizations
        4. Generate distance frequency histogram
        5. Analyze density statistics
        
        [PARAMETERS]
        results : List[Tuple[str, Dict[str, Any]]]
            Results from each tomogram
            
        [OUTPUT]
        Dict[str, Any]:
            'data': Combined DataFrame with all methods
            'average': Average values for all methods
            'density_stats': Density statistics per tomogram
        """
        dfs, all_distances, density_data, skipped = self._collect_tomogram_data(results)
        combined_df = pd.concat(dfs, ignore_index=True)
        
        avg_df = self._calculate_averages(combined_df)
        self._save_average_distributions(avg_df)
        
        if len(all_distances) > 0:
            distances_array = np.array(all_distances)
            mask = (distances_array >= self.config.min_distance) & (distances_array <= self.config.max_distance)
            filtered_distances = distances_array[mask]
            
            if len(filtered_distances) > 0:
                hist_file = str(self.output_dirs['combined'] / 'distance_frequency')
                plot_histogram(
                    filtered_distances,
                    hist_file,
                    plot_type='distance',
                    title='Distribution of Particle-Particle Distances',
                    xlabel='Distance (Å)',
                    ylabel='Frequency'
                )
                self.logger.info(f"Distance frequency histogram saved to {hist_file}.jpg")
        
        density_stats = self._analyze_density_stats(density_data)
        if density_stats:
            density_df = pd.DataFrame(density_data)
            density_file = self.output_dirs['combined'] / 'density_statistics.txt'
            density_df.to_csv(density_file, sep='\t', index=False)
            self.logger.info(f"Density statistics saved to {density_file}")
        
        return {
            'data': combined_df,
            'average': avg_df,
            'density_stats': density_stats,
            'skipped_tomograms': skipped
        }
        
    def _is_valid_density(self, result: Dict[str, Any]) -> bool:
        """Check if density data is valid.
        
        [PARAMETERS]
        result : Dict[str, Any]
            Analysis result for a single tomogram
            
        [OUTPUT]
        bool:
            True if density data is valid
        """
        return ('particle_density' in result and 
                np.isfinite(result['particle_density']) and 
                result['particle_density'] > 0)
    
    def _collect_tomogram_data(self, 
                             results: List[Tuple[str, Dict[str, Any]]]
                             ) -> Tuple[List[pd.DataFrame], List[float], List[Dict], List[str]]:
        """Collect data from all tomograms.
        
        [WORKFLOW]
        1. Collect distribution data from each tomogram
        2. Collect raw distances
        3. Collect density data
        4. Track skipped tomograms
        
        [PARAMETERS]
        results : List[Tuple[str, Dict[str, Any]]]
            Analysis results from all tomograms
            
        [OUTPUT]
        Tuple[List[pd.DataFrame], List[float], List[Dict], List[str]]:
            - List of distribution DataFrames
            - All raw distances
            - Density data
            - Skipped tomogram names
        """
        dfs = []
        all_distances = []
        density_data = []
        skipped = []
        
        for tomogram, result in results:
            if result.get('insufficient_particles', False):
                skipped.append(tomogram)
                self.logger.info(f"Skipping tomogram {tomogram} due to insufficient particles")
                continue
                
            data_dict = {'Distance': result['distances'], 'Tomogram': tomogram}
            for _, config in self.DISTRIBUTIONS.items():
                data_dict[config['key']] = result[config['key']]
            dfs.append(pd.DataFrame(data_dict))
            
            if 'raw_distances' in result:
                all_distances.extend(result['raw_distances'])
                
            if self._is_valid_density(result):
                density_data.append({
                    'Tomogram': tomogram,
                    'Particle_Density': result['particle_density']
                })
                
        return dfs, all_distances, density_data, skipped
    
    def _calculate_averages(self, combined_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate averages and std for all distributions.
        
        [PARAMETERS]
        combined_df : pd.DataFrame
            Combined distribution data
            
        [OUTPUT]
        pd.DataFrame:
            DataFrame with means and standard deviations
        """
        avg_df = combined_df.groupby('Distance')[
            [config['key'] for config in self.DISTRIBUTIONS.values()]
        ].agg(['mean', 'std', 'count']).reset_index()
        
        avg_df.columns = ['Distance'] + [
            '_'.join(col).strip() for col in avg_df.columns[1:]
        ]
        return avg_df
    
    def _analyze_peak_stats(self, 
                          data: pd.DataFrame,
                          avg_data: pd.DataFrame,
                          dist_type: str) -> Dict[str, str]:
        """Analyze peak statistics for a distribution.
        
        [PARAMETERS]
        data : pd.DataFrame
            Raw data
        avg_data : pd.DataFrame
            Averaged data
        dist_type : str
            Distribution type
            
        [OUTPUT]
        Dict[str, str]:
            Peak statistics
        """
        max_idx = avg_data[f'{dist_type}_mean'].idxmax()
        return {
            f"Maximum {dist_type}": f"{data[dist_type].max():.2e}",
            "Peak position": f"{avg_data.loc[max_idx, 'Distance']:.1f} Å",
            "Peak height": f"{avg_data.loc[max_idx, f'{dist_type}_mean']:.2e} ± {avg_data.loc[max_idx, f'{dist_type}_std']:.2e}"
        }
        
    def _analyze_density_stats(self, density_data: List[Dict]) -> Optional[Dict[str, float]]:
        """Analyze particle density statistics.
        
        [PARAMETERS]
        density_data : List[Dict]
            List of density data
            
        [OUTPUT]
        Optional[Dict[str, float]]:
            Density statistics, None if no valid data
        """
        if not density_data:
            return None
            
        density_df = pd.DataFrame(density_data)
        return {
            'mean_density': density_df['Particle_Density'].mean(),
            'std_density': density_df['Particle_Density'].std(),
            'min_density': density_df['Particle_Density'].min(),
            'max_density': density_df['Particle_Density'].max()
        }
    
    def _format_section_data(self, results: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Format data for report sections.
        
        [PARAMETERS]
        results : Dict[str, Any]
            Analysis results
            
        [OUTPUT]
        Dict[str, Dict[str, Any]]:
            Section titles and content
        """
        data = results['data']
        avg_data = results['average']
        skipped_tomograms = results.get('skipped_tomograms', [])
        
        sections = {
            "Radial Distribution Function Analysis": {
                "Bin size": f"{self.config.bin_size} Å",
                "Minimum distance": f"{self.config.min_distance} Å",
                "Maximum distance": f"{self.config.max_distance} Å"
            },
            
            "Dataset Statistics": {
                "Number of tomograms analyzed": len(data['Tomogram'].unique()),
                "Total measurements": len(data)
            }
        }
        
        if skipped_tomograms:
            sections["Dataset Statistics"].update({
                "Skipped tomograms (insufficient particles)": len(skipped_tomograms),
                "Skipped tomogram names": ", ".join(skipped_tomograms)
            })
            
        density_stats = results.get('density_stats')
        if density_stats:
            sections["Particle Density Statistics"] = {
                "Mean density": f"{density_stats['mean_density']:.2e} particles/Å³",
                "Std density": f"{density_stats['std_density']:.2e} particles/Å³",
                "Min density": f"{density_stats['min_density']:.2e} particles/Å³",
                "Max density": f"{density_stats['max_density']:.2e} particles/Å³",
                "Density range ratio": f"{density_stats['max_density']/density_stats['min_density']:.2f}"
            }
            
        for dist_type, config in self.DISTRIBUTIONS.items():
            title = f"{config['label']} Statistics"
            if dist_type == 'rdf':
                title += " (Shell Volume Normalization)"
            elif dist_type == 'local_density':
                title += " (Expected Pairs Normalization)"
            elif dist_type == 'distance_weighted':
                title += " (r² Normalization)"
                
            sections[title] = self._analyze_peak_stats(
                data, avg_data, config['key']
            )
        
        return sections
    
    def _save_average_distributions(self, avg_df: pd.DataFrame) -> None:
        """Save averaged distribution data and plots.
        
        [PARAMETERS]
        avg_df : pd.DataFrame
            DataFrame containing means and standard deviations
        """
        avg_file = self.output_dirs['combined'] / 'average_all_methods.txt'
        avg_df.to_csv(avg_file, sep='\t', index=False)
        
        for dist_type, config in self.DISTRIBUTIONS.items():
            key = config['key']
            dist_df = avg_df[['Distance', f'{key}_mean', f'{key}_std']].copy()
            dist_df.columns = ['Distance', 'mean', 'std']
            
            data_file = self._save_data(
                {'Distance': dist_df['Distance'], 'mean': dist_df['mean'], 'std': dist_df['std']},
                f'average_{dist_type}',
                prefix='combined'
            )
            
            plot_xy(
                str(data_file),
                str(self.output_dirs['combined'] / f"average_{dist_type}.png"),
                xlabel='r (Å)',
                ylabel=config['ylabel']
            )
    
    def _generate_report(self, results: Dict[str, Any]) -> None:
        """Generate RDF analysis report.
        
        [WORKFLOW]
        1. Format section data
        2. Write report sections
        3. Log completion
        
        [PARAMETERS]
        results : Dict[str, Any]
            Combined analysis results with all normalization methods
        """
        sections = self._format_section_data(results)
        
        report_file = self.output_dir / 'rdf_report.txt'
        with open(report_file, 'w') as f:
            for title, content in sections.items():
                if content:  # Only write sections with content
                    self._write_report_section(f, title, content)
        
        self.logger.info(f"Analysis report saved to {report_file}")
