import numpy as np
import pandas as pd
from typing import Tuple

from .base import BaseComparer
from ...utils.errors import AnalysisError
from ...core.io import format_input_star, format_output_star
from ...core.transform import add_particle_names, merge_for_match
from ...core.matrix_math import euler_to_vector, calculate_orientation_angle
from ...utils.plot import plot_histogram, plot_polar

class OrientationComparer(BaseComparer):
    """
    Compares particle orientations between two corresponding STAR files.

    [Workflow]
    1. Load particles from two STAR files.
    2. Match particles based on their names.
    3. Calculate the angle between the orientation vectors of matched pairs.
    4. Save the results, including STAR files with added angle information.
    5. Generate and save plots (histogram and polar plot) of the angle distribution.

    [Parameters]
    env_star : str
        Path to the 'environment' STAR file.
    membrane_star : str
        Path to the 'membrane' STAR file.
    output_dir : str, optional
        Directory to save results. Defaults to 'orientation_comparison'.
    
    [Example]
    >>> comparer = OrientationComparer("env.star", "mem.star")
    """

    def __init__(self, env_star: str, membrane_star: str, output_dir: str = 'orientation_comparison'):
        """
        Initializes the OrientationComparer.

        [PARAMETER]
        env_star : str
            Path to the 'environment' STAR file.
        membrane_star : str
            Path to the 'membrane' STAR file.
        output_dir : str, optional
            Directory to save results. Defaults to 'orientation_comparison'.
        
        [EXAMPLE]
        >>> comparer = OrientationComparer("env.star", "mem.star")
        >>> comparer.compare()
        """
        super().__init__(file1=env_star, file2=membrane_star, output_dir=output_dir)
        self.env_star_path = self.file1
        self.membrane_star_path = self.file2

    def compare(self) -> dict:
        """
        Executes the orientation comparison workflow.

        [WORKFLOW]
        1. Load particle data from both STAR files.
        2. Calculate angles between matched particles.
        3. Save results if matching particles are found.
        4. Generate plots for the angle distribution.

        [OUTPUT]
        dict: 
            A dictionary containing:
            - 'angles': A list of calculated orientation angles.
            - 'output_files': A dictionary with paths to the saved files.
        
        [RAISES]
        AnalysisError: If no matching particles are found.
        """
        self.logger.info("Loading particle data...")
        env_data, membrane_data = (
            format_input_star(self.env_star_path),
            format_input_star(self.membrane_star_path)
        )

        self.logger.info("Calculating inter-particle angles...")
        angles, matched_env, matched_mem = self._calculate_angles(
            env_data['particles'], membrane_data['particles']
        )

        if not angles:
            raise AnalysisError("No matching particles found for angle calculation.")

        self.logger.info(f"Found {len(angles)} matching particles.")
        
        output_paths = self.save_results(
            angles,
            {'optics': env_data.get('optics'), 'particles': matched_env},
            {'optics': membrane_data.get('optics'), 'particles': matched_mem}
        )
        
        self.plot_results(np.array(angles))

        return {"angles": angles, "output_files": output_paths}

    def _get_euler_angles(self, row: pd.Series, prefix: str) -> tuple:
        """Extract Euler angles from row with given prefix.
        
        [PARAMETER]
        row : pd.Series
            DataFrame row containing angle data
        prefix : str
            Suffix for column names ('ref' or 'full')
            
        [OUTPUT]
        tuple:
            Three Euler angles (rot, tilt, psi)
        """
        return (
            row[f'rlnAngleRot_{prefix}'],
            row[f'rlnAngleTilt_{prefix}'],
            row[f'rlnAnglePsi_{prefix}']
        )
    
    def _add_angles_to_particles(self,
                               particles: pd.DataFrame, 
                               merged: pd.DataFrame,
                               name_suffix: str) -> pd.DataFrame:
        """Add angle comparison results to particle data.
        
        [PARAMETER]
        particles : pd.DataFrame
            Original particle data
        merged : pd.DataFrame
            Merged data containing angle comparisons
        name_suffix : str
            Suffix for image name column ('ref' or 'full')
            
        [OUTPUT]
        pd.DataFrame:
            Particles DataFrame with added angle comparison column
        """
        image_name_col = f'rlnImageName_{name_suffix}'
        merge_cols = [image_name_col, 'rlnAngleCompare']
        
        return (particles
               .merge(
                   merged[merge_cols],
                   left_on='rlnImageName',
                   right_on=image_name_col,
                   how='left'
               )
               .drop(columns=[image_name_col])
               .dropna(subset=['rlnAngleCompare']))

    def _calculate_angles(self, env_particles: pd.DataFrame, membrane_particles: pd.DataFrame) -> Tuple[list, pd.DataFrame, pd.DataFrame]:
        """
        Calculates orientation angles between matched particles.

        [WORKFLOW]
        1. Add unique particle names for matching.
        2. Merge DataFrames to find corresponding particles.
        3. For each matched pair, convert Euler angles to vectors.
        4. Calculate the angle between the two vectors.
        5. Add the calculated angle to the particle data.

        [PARAMETER]
        env_particles : pd.DataFrame
            DataFrame of particles from the environment STAR file.
        membrane_particles : pd.DataFrame
            DataFrame of particles from the membrane STAR file.

        [OUTPUT]
        Tuple[list, pd.DataFrame, pd.DataFrame]:
            - A list of calculated angles.
            - The environment particles DataFrame with an added 'rlnAngleCompare' column.
            - The membrane particles DataFrame with an added 'rlnAngleCompare' column.
        """
        env_particles_named = add_particle_names(env_particles)
        membrane_particles_named = add_particle_names(membrane_particles)

        merged_particles = merge_for_match(
            ref_particles=env_particles_named,
            full_particles=membrane_particles_named,
            merge_keys=['particle_name']
        )

        if merged_particles.empty:
            return [], pd.DataFrame(), pd.DataFrame()

        angles = [
            calculate_orientation_angle(
                euler_to_vector(*self._get_euler_angles(row, 'full')),
                euler_to_vector(*self._get_euler_angles(row, 'ref'))
            )
            for _, row in merged_particles.iterrows()
        ]
        merged_particles['rlnAngleCompare'] = angles

        datasets = [
            (env_particles, 'ref'),
            (membrane_particles, 'full')
        ]
        processed_particles = [
            self._add_angles_to_particles(particles, merged_particles, suffix)
            for particles, suffix in datasets
        ]

        return angles, *processed_particles

    def save_results(self, angles: list, env_data: dict, membrane_data: dict) -> dict:
        """
        Saves the analysis results to files.

        [WORKFLOW]
        1. Define output paths for the new STAR files and the angles text file.
        2. Write the updated environment and membrane particle data to new STAR files.
        3. Save the list of angles to a text file.

        [PARAMETER]
        angles : list
            A list of calculated orientation angles.
        env_data : dict
            Dictionary containing optics and particle data for the environment set.
        membrane_data : dict
            Dictionary containing optics and particle data for the membrane set.

        [OUTPUT]
        dict: 
            A dictionary mapping result types to their file paths.
        """
        base_name = f"AngleAnalysis_{self.env_star_path.stem}_{self.membrane_star_path.stem}"
        
        paths = {
            "env_star_out": self.output_dir / f"{self.env_star_path.stem}_with_angles.star",
            "membrane_star_out": self.output_dir / f"{self.membrane_star_path.stem}_with_angles.star",
            "angles_txt": self.output_dir / f"{base_name}.txt"
        }

        format_output_star(env_data, paths['env_star_out'])
        format_output_star(membrane_data, paths['membrane_star_out'])

        np.savetxt(paths['angles_txt'], angles, delimiter='\t', fmt='%.4f')
        
        self.logger.info(f"Results saved in: {self.output_dir}")
        return paths

    def plot_results(self, angles: np.ndarray):
        """
        Generates and saves plots for the analysis.

        [WORKFLOW]
        1. Create a histogram of the angle distribution.
        2. Create a polar plot to visualize angular distribution.

        [PARAMETER]
        angles : np.ndarray
            An array of calculated orientation angles.
        """
        base_name = f"AngleAnalysis_{self.env_star_path.stem}_{self.membrane_star_path.stem}"
        
        plot_histogram(
            angles,
            str(self.output_dir / f"{base_name}_histogram.jpg"),
            plot_type='angle',
            title='Orientation Angle Distribution',
            xlabel='Angle (degrees)',
            ylabel='Frequency'
        )
        plot_polar(angles, str(self.output_dir / f"{base_name}_polar.jpg"))
        
        self.logger.info("Plots generated.")
