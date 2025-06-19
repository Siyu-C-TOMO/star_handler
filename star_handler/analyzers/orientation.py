"""
Orientation analysis for particles.

Analyzes angular relationships between particle orientations,
focusing on nearest-neighbor interactions.
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

from star_handler.analyzers.base import BaseAnalyzer
from star_handler.core.matrix_math import (
    euler_to_vector,
    calculate_orientation_angle
)
from star_handler.utils.plot import plot_histogram
from star_handler.utils.config import OrientationConfig

class OrientationAnalyzer(BaseAnalyzer):
    """Analyze particle orientations in RELION STAR file.
    
    [WORKFLOW]
    1. Read particle orientations from STAR file
    2. Calculate angular distributions
    3. Generate orientation plots and statistics

    [PARAMETERS]
    star_file : str
        Path to input STAR file
    output_dir : Union[str, Path]
        Base output directory
    max_angle : Optional[float]
        Maximum angle to consider
    bin_width : Optional[float]
        Width of angle bins

    [OUTPUT]
    - orientations.pdf: Angular distribution plots
    - angle_stats.csv: Orientation statistics

    [EXAMPLE]
    Analyze particle orientations with default parameters:
        $ star-handler star-orientation -f particles.star
    """
    
    ANALYSIS_TYPE = "orientation"
    CONFIG_CLASS = OrientationConfig
    
    REQUIRED_COLUMNS = {
        'rlnCoordinateX', 'rlnCoordinateY', 'rlnCoordinateZ',
        'rlnAngleRot', 'rlnAngleTilt', 'rlnAnglePsi'
    }
    
    MEASUREMENTS = {
        'angle': {
            'key': 'angles',
            'label': 'Orientation Angle',
            'ylabel': 'Count',
            'plot_type': 'angle',
            'title': 'Distribution of Orientation Angles'
        },
        'distance': {
            'key': 'distances',
            'label': 'Neighbor Distance',
            'ylabel': 'Count',
            'plot_type': 'distance',
            'title': 'Distribution of Nearest Neighbor Distances'
        }
    }
    
    def __init__(self, star_file: str, **kwargs) -> None:
        """Initialize OrientationAnalyzer.
        
        Args:
            star_file: Path to input STAR file
            **kwargs: Optional configuration parameters
                     - output_dir: Output directory (default: 'analysis')
                     - max_angle: Maximum angle to consider (degrees)
                     - bin_width: Width of angle bins (degrees)
        """
        super().__init__(star_file, **kwargs)
        
    def _analyze(self,
                data: pd.DataFrame,
                coords: np.ndarray,
                dist_matrix: np.ndarray) -> Dict[str, Any]:
        """Analyze particle orientations.
        
        [WORKFLOW]
        1. Convert Euler angles to vectors
        2. Find nearest neighbors
        3. Calculate angles between vectors
        
        [PARAMETERS]
        data : pd.DataFrame
            Full particle data with Euler angles
        coords : np.ndarray
            Coordinate array
        dist_matrix : np.ndarray
            Distance matrix
            
        [OUTPUT]
        Dict[str, Any]:
            'angles': Orientation angles
            'distances': Corresponding distances
        """
        missing = self.REQUIRED_COLUMNS - set(data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
            
        vectors = np.array([
            euler_to_vector(
                row['rlnAngleRot'],
                row['rlnAngleTilt'],
                row['rlnAnglePsi']
            )
            for _, row in data.iterrows()
        ])
        
        dist = dist_matrix.copy()
        np.fill_diagonal(dist, np.inf)
        nearest_neighbors = np.argmin(dist, axis=1)
        nearest_distances = np.min(dist, axis=1)
        
        angles = np.array([
            calculate_orientation_angle(vectors[i], vectors[nn])
            for i, nn in enumerate(nearest_neighbors)
        ])
        
        results = {
            'angles': angles,
            'distances': nearest_distances
        }
        
        if not all(isinstance(v, np.ndarray) and len(v) > 0 for v in results.values()):
            raise ValueError("All results must be non-empty numpy arrays")
        return results
        
    def _save_tomogram_results(self,
                             tomogram: str,
                             results: Dict[str, Any]) -> None:
        """Save orientation results for a tomogram.
        
        [WORKFLOW]
        1. Save measurements data
        2. Create visualizations for each measurement
        
        [PARAMETERS]
        tomogram : str
            Tomogram identifier
        results : Dict[str, Any]
            Analysis results with angles and distances
        """
        save_data = {
            config['key']: (results[config['key']].tolist() 
                          if isinstance(results[config['key']], np.ndarray) 
                          else results[config['key']])
            for config in self.MEASUREMENTS.values()
        }
        self._save_data(save_data, tomogram)
        
        for measurement_type, config in self.MEASUREMENTS.items():
            plot_histogram(
                results[config['key']],
                str(self.output_dirs['plots'] / f"{tomogram}_{measurement_type}"),
                plot_type=config['plot_type'],
                title=config['title'],
                xlabel=config['label'],
                ylabel=config['ylabel']
            )
            
    def _combine_results(self,
                        results: List[Tuple[str, Dict[str, Any]]]
                        ) -> Dict[str, Any]:
        """
        Combine orientation results from all tomograms.
        
        [WORKFLOW]
        1. Collect all angle data
        2. Calculate statistics
        3. Generate combined plots
        
        [PARAMETERS]
        results : List[Tuple[str, Dict[str, Any]]]
            Results from each tomogram
            
        [OUTPUT]
        Dict[str, Any]:
            'data': Combined angle data
            'statistics': Overall statistics
        """
        combined_data = []
        
        self.logger.info(f"Processing {len(results)} tomogram results")
        
        required_keys = {config['key'] for config in self.MEASUREMENTS.values()}
        
        for result in results:
            tomogram, data = result
            missing_keys = required_keys - set(data.keys())
            if missing_keys:
                raise ValueError(f"Data from {tomogram} missing required keys: {missing_keys}")
            
            row = {'Tomogram': tomogram}
            for config in self.MEASUREMENTS.values():
                key = config['key']
                row[key] = data[key].tolist() if isinstance(data[key], np.ndarray) else data[key]
                if not isinstance(row[key], list):
                    raise ValueError(f"Expected list data for {key} in {tomogram}")
                    
            combined_data.append(row)
            self.logger.debug(f"Added row for {tomogram}: {row.keys()}")
                
        self.logger.info("Creating DataFrame...")
        try:
            combined_df = pd.DataFrame(combined_data)
            
            measurement_keys = ['Tomogram'] + [config['key'] for config in self.MEASUREMENTS.values()]
            combined_df = combined_df[measurement_keys]  # Ensure correct column order
            
            self._save_data({
                'Tomogram': combined_df['Tomogram'].tolist(),
                **{key: combined_df[key].tolist() for key in measurement_keys[1:]}
            }, 'measurements', prefix='combined')
            
        except Exception as e:
            self.logger.error(f"Error creating combined DataFrame: {str(e)}")
            self.logger.error(f"Combined data preview: {combined_data[:1]}")
            raise ValueError(f"Failed to create combined data: {str(e)}")
        
        for measurement_type, config in self.MEASUREMENTS.items():
            plot_histogram(
                np.concatenate([
                    np.asarray(d[config['key']]).flatten()
                    for _, d in results
                ]),
                str(self.output_dirs['combined'] / f"{measurement_type}_distribution"),
                plot_type=config['plot_type'],
                title=f"{config['title']} (All Tomograms)",
                xlabel=config['label'],
                ylabel=config['ylabel']
            )
        
        combined_results = {
            'data': combined_df,
            'tomogram_results': results
        }
        
        stats = {}
        for measurement_type, config in self.MEASUREMENTS.items():
            values = np.concatenate([
                np.asarray(d[config['key']]).flatten()
                for _, d in results
            ])
            stats.update({
                f"mean_{measurement_type}": float(np.mean(values)),
                f"std_{measurement_type}": float(np.std(values)),
                **({'median_angle': float(np.median(values))} if measurement_type == 'angle' else {})
            })
        
        combined_results['statistics'] = stats
        return combined_results
        
    def _generate_report(self, results: Dict[str, Any]) -> None:
        """Generate orientation analysis report.
        
        [WORKFLOW]
        1. Calculate statistics
        2. Write detailed report
        
        [PARAMETERS]
        results : Dict[str, Any]
            Combined analysis results
        """
        report_file = self.output_dir / 'orientation_report.txt'
        try:
            with open(report_file, 'w') as f:
                data = results['data']
                stats = results['statistics']
                tomogram_results = results['tomogram_results']
                self._write_report_section(f, "Particle Orientation Analysis", {
                    "Maximum angle": f"{self.config.max_angle or 'auto'}°",
                    "Bin width": f"{self.config.bin_width or 'auto'}°"
                })
                
                total_measurements = sum(
                    len(data[self.MEASUREMENTS['angle']['key']])
                    for _, data in tomogram_results
                )
                self._write_report_section(f, "Dataset Statistics", {
                    "Number of tomograms": len(data['Tomogram'].unique()),
                    "Total measurements": total_measurements
                })
                for measurement_type, config in self.MEASUREMENTS.items():
                    label = config['label']
                    mean = stats[f"mean_{measurement_type}"]
                    std = stats[f"std_{measurement_type}"]
                    section_content = {
                        f"Mean {label.lower()}": f"{mean:.2f} ± {std:.2f}"
                    }
                    
                    if measurement_type == 'angle':
                        section_content['Median angle'] = f"{stats['median_angle']:.2f}°"
                        
                        angle_values = np.concatenate([
                            np.asarray(d[config['key']]).flatten()
                            for _, d in tomogram_results
                        ])
                        angle_bins = pd.cut(
                            pd.Series(angle_values),
                            bins=np.arange(0, 181, 10),
                            right=False
                        ).value_counts().sort_index()
                        
                        self._write_report_section(f, "Angular Distribution", {
                            str(interval): f"{count} pairs"
                            for interval, count in angle_bins.items()
                        })
                    
                    section_title = f"{label} Statistics"
                    self._write_report_section(f, section_title, section_content)
        except Exception as e:
            self.logger.error(f"Failed to generate report: {str(e)}")
            raise ValueError(f"Report generation failed: {str(e)}")
        else:
            self.logger.info(f"Analysis report saved to {report_file}")
