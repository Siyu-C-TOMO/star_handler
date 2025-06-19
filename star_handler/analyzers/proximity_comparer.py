"""
Compares two sets of coordinates to find proximity.
"""

from pathlib import Path
from typing import Tuple, Dict, Any, Union

import numpy as np
import pandas as pd

from .base import BaseComparer, AnalysisError
from ..core.io import format_input_star, format_output_star
from ..core import matrix_math

class ProximityComparer(BaseComparer):
    """
    Calculates the percentage of particles in one STAR file (A) that have a 
    neighbor in a second STAR file (B) within a given distance threshold.

    [Workflow]
    1. Load particles from two STAR files (Set A and Set B).
    2. Extract 2D coordinates (X, Y) from both sets.
    3. Build a KD-Tree from the coordinates of Set B for efficient searching.
    4. For each particle in Set A, query the KD-Tree to find the distance to the
       nearest neighbor in Set B.
    5. Count how many particles in Set A have a neighbor within the specified
       distance threshold.
    6. Calculate the final percentage.
    7. Save a new STAR file for Set A, with an added 'rlnHasNeighbor' column 
       (1 for true, 0 for false).
    8. Generate a text report summarizing the results.

    [Parameters]
    star_file_a : str
        Path to the primary STAR file (Set A).
    star_file_b : str
        Path to the secondary STAR file to compare against (Set B).
    threshold : float
        The distance threshold in pixels to consider a particle a neighbor.
    output_dir : str, optional
        Directory to save results. Defaults to 'proximity_comparison'.
    
    [EXAMPLE]
    >>> comparer = ProximityComparer(
    ...     star_file_a="set_a.star",
    ...     star_file_b="set_b.star",
    ...     threshold=50.0
    ... )
    >>> results = comparer.compare()
    >>> print(f"Proximity: {results['percentage']:.2f}%")
    """

    def __init__(self, 
                 star_file_a: Union[str, Path], 
                 star_file_b: Union[str, Path], 
                 threshold: float, 
                 output_dir: Union[str, Path] = 'proximity_comparison'):
        """
        Initializes the ProximityComparer.

        [PARAMETER]
        star_file_a : Union[str, Path]
            Path to the primary STAR file (Set A).
        star_file_b : Union[str, Path]
            Path to the secondary STAR file (Set B).
        threshold : float
            The distance threshold in pixels.
        output_dir : Union[str, Path], optional
            Directory to save results. Defaults to 'proximity_comparison'.
        """
        super().__init__(file1=Path(star_file_a), 
                         file2=Path(star_file_b), 
                         output_dir=Path(output_dir))
        self.threshold = threshold
        self.logger.info(f"Initialized ProximityComparer with threshold: {self.threshold} pixels.")

    def compare(self) -> Dict[str, Any]:
        """
        Executes the proximity comparison workflow.

        [WORKFLOW]
        1. Load particle data from both STAR files.
        2. Calculate proximity percentage and identify neighbors.
        3. Save the results.
        4. Generate and save a report.

        [OUTPUT]
        dict: 
            A dictionary containing:
            - 'percentage': The calculated percentage of neighboring particles.
            - 'neighbor_count': The absolute number of neighboring particles.
            - 'total_count': The total number of particles in set A.
            - 'output_files': A dictionary with paths to the saved files.
        
        [RAISES]
        AnalysisError: If STAR file A fails to load or contains no particles.
        """
        self.logger.info(f"Loading particles from Set A: {self.file1}")
        data_a = format_input_star(self.file1)
        
        self.logger.info(f"Loading particles from Set B: {self.file2}")
        data_b = format_input_star(self.file2)

        particles_a = data_a.get('particles')
        particles_b = data_b.get('particles')

        if particles_a is None or particles_a.empty:
            raise AnalysisError(f"No particles found in STAR file A: {self.file1}")
        
        if particles_b is None or particles_b.empty:
            self.logger.warning(f"No particles found in STAR file B: {self.file2}. Result will be 0%.")
            percentage = 0.0
            neighbor_count = 0
            has_neighbor_col = pd.Series([False] * len(particles_a), index=particles_a.index)
        else:
            self.logger.info("Calculating proximity using KD-Tree...")
            percentage, neighbor_count, has_neighbor_col = self._calculate_proximity(
                particles_a, particles_b
            )

        self.logger.info(f"Calculation complete: {neighbor_count}/{len(particles_a)} ({percentage:.2f}%) of particles in A have a neighbor in B.")

        output_paths = self.save_results(
            particles_a,
            data_a.get('optics'),
            has_neighbor_col
        )
        
        report_data = {
            "percentage": percentage,
            "neighbor_count": neighbor_count,
            "total_count": len(particles_a),
        }
        self._generate_report(report_data)

        return {**report_data, "output_files": output_paths}

    def _calculate_proximity(self, 
                             particles_a: pd.DataFrame, 
                             particles_b: pd.DataFrame) -> Tuple[float, int, pd.Series]:
        """
        Calculates proximity by leveraging the core math module.

        [PARAMETER]
        particles_a : pd.DataFrame
            DataFrame of particles from Set A.
        particles_b : pd.DataFrame
            DataFrame of particles from Set B.

        [OUTPUT]
        Tuple[float, int, pd.Series]:
            - The percentage of A particles with a neighbor in B.
            - The count of A particles with a neighbor in B.
            - A boolean Series indicating which A particles have a neighbor.
        """
        coords_a = particles_a[['rlnCoordinateX', 'rlnCoordinateY']].values
        coords_b = particles_b[['rlnCoordinateX', 'rlnCoordinateY']].values

        distances = matrix_math.find_nearest_neighbor_distances(coords_a, coords_b)

        has_neighbor = distances <= self.threshold
        neighbor_count = int(np.sum(has_neighbor))
        
        total_count = len(particles_a)
        percentage = (neighbor_count / total_count) * 100 if total_count > 0 else 0.0

        return percentage, neighbor_count, pd.Series(has_neighbor, index=particles_a.index)

    def save_results(self, 
                     particles_a: pd.DataFrame, 
                     optics_a: pd.DataFrame, 
                     has_neighbor_col: pd.Series) -> Dict[str, Path]:
        """
        Saves the analysis results to files.

        [PARAMETER]
        particles_a : pd.DataFrame
            The original particle data for set A.
        optics_a : pd.DataFrame
            The optics data for set A, can be None.
        has_neighbor_col : pd.Series
            A boolean series indicating neighbor status for each particle in A.

        [OUTPUT]
        dict: 
            A dictionary mapping result types to their file paths.
        """
        self.logger.info("Saving results...")
        
        particles_a_with_results = particles_a.copy()
        particles_a_with_results['rlnHasNeighbor'] = has_neighbor_col.astype(int)

        output_star_data = {'particles': particles_a_with_results}
        if optics_a is not None:
            output_star_data['optics'] = optics_a

        output_star_path = self.output_dir / f"{self.file1.stem}_with_proximity.star"
        format_output_star(output_star_data, output_star_path)
        
        self.logger.info(f"Saved updated STAR file to: {output_star_path}")
        
        return {"output_star": output_star_path}

    def _generate_report(self, results: Dict[str, Any]):
        """
        Generates a simple text report of the analysis.

        [PARAMETER]
        results : dict
            A dictionary containing the calculated 'percentage', 'neighbor_count', and 'total_count'.
        """
        report_path = self.output_dir / "proximity_report.txt"
        self.logger.info(f"Generating report at: {report_path}")

        with open(report_path, 'w') as f:
            f.write("=== Proximity Analysis Report ===\n\n")
            f.write(f"Set A File: {self.file1.name}\n")
            f.write(f"Set B File: {self.file2.name}\n")
            f.write(f"Distance Threshold: {self.threshold} pixels\n\n")
            f.write("--- Results ---\n")
            f.write(f"Particles in Set A with a neighbor in Set B: {results['neighbor_count']} / {results['total_count']}\n")
            f.write(f"Percentage: {results['percentage']:.2f}%\n")
        
        self.logger.info("Report generation complete.")
