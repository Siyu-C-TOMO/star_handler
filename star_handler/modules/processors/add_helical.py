from pathlib import Path
from typing import Union
import numpy as np

from .base import BaseProcessor
from ...utils.errors import FormatError, ProcessingError
from ...core.io import format_input_star, format_output_star
from ...core.transform import merge_for_match

class AddHelByRefProcessor(BaseProcessor):
    """Filter particles in STAR file based on a reference STAR file.
    
    [WORKFLOW]
    1. Check if input STAR files exist and are valid
    2. Read and format both reference and full STAR files
    4. Merge and add helical ID based on three rotation angles and particle name
    5. Save matched particles to output star file

    [PARAMETERS]
    full_star : str
        Path to STAR file to be filtered
    ref_star : str
        Path to reference STAR file
    output_dir : str, optional
        Output directory for results

    [OUTPUT]
    - Filtered STAR file in output directory
    - File named as original_name_matched.star

    [EXAMPLE]
    Custom output directory:
        $ star-handler process-add-column-by-ref -f particles.star -r reference.star -o added_columns
    """
  
    def __init__(self, full_star: str, ref_star: str, output_dir: str = 'added'):
        """Initialize processor with full and ref star file paths.

        [PARAMETERS]
        full_star : str
            Path to the full star file to be filtered
        ref_star : str
            Path to the reference star file
        output_dir : str, optional
            Directory to save output files (default: 'added')
            
        [RAISES]
        FormatError
            If either full_star or ref_star file does not exist
        """
        super().__init__()
        self.validate_files(full_star, ref_star)
        
        self.full_star = full_star
        self.ref_star = ref_star
        self.output_dir = output_dir
        self.matching_keys = ['rlnAngleRot', 'rlnAngleTilt', 'rlnAnglePsi','rlnMicrographName']
        
    def _validate_column_requirements(self, full_data: dict, ref_data: dict) -> None:
        """Validate required columns exist in both datasets.
        
        [PARAMETERS]
        full_data : dict
            Full star file data
        ref_data : dict
            Reference star file data
            
        [RAISES]
        FormatError
            If required columns are missing
        """

        for col in self.matching_keys:
            if col not in full_data['particles'].columns:
                raise FormatError(f"Missing required column {col} in full star file")
            if col not in ref_data['particles'].columns:
                raise FormatError(f"Missing required column {col} in reference star file")

    def process(self) -> Union[str, Path]:
        """
        Execute main processing workflow.
        
        [WORKFLOW]
        1. Validate input files
        2. Process and match particles
        3. Save filtered results
        
        [OUTPUT]
        Union[str, Path]: Path to the output star file
        
        [RAISES]
        FormatError
            If input files are invalid or missing required columns
        ProcessingError
            If matching or processing fails
        """
        try:
            self.logger.info("Reading star files...")
            full_data = format_input_star(self.full_star)
            ref_data = format_input_star(self.ref_star)
            
            self._validate_column_requirements(full_data, ref_data)

            ref_to_merge = ref_data['particles'][self.matching_keys+['rlnHelicalTubeID']]

            angle_cols = ['rlnAngleRot', 'rlnAngleTilt', 'rlnAnglePsi']
            ref_to_merge[angle_cols] = ref_to_merge[angle_cols].round(3)
            full_data['particles'][angle_cols] = full_data['particles'][angle_cols].round(3)

            self.logger.info("Matching particles...")
            matched_particles = merge_for_match(
                ref_particles=ref_to_merge,
                full_particles=full_data['particles'],
                merge_keys=self.matching_keys,
                keep_unmatched=False
            )
            if 'rlnOpticsGroup' not in matched_particles:
                matched_particles['rlnOpticsGroup'] = 1
            matched_particles['rlnAngleTiltPrior'] = matched_particles['rlnAngleTilt']
            matched_particles['rlnAnglePsiPrior'] = matched_particles['rlnAnglePsi']
            matched_particles['rlnHelicalTrackLengthAngst'] = 0
            spacing = 82.0
            for tube_id, group in matched_particles.groupby('rlnHelicalTubeID'):
                matched_particles.loc[group.index, 'rlnHelicalTrackLengthAngst'] = np.arange(len(group)) * spacing
            matched_particles['rlnAnglePsiFlipRatio'] = 0.9
            
            self.logger.info(f"Found {len(matched_particles)} matching particles")

            output_path = self.get_output_path(
                self.full_star, 
                '_matched',
                self.output_dir
            )
            
            matched_star_file = {}
            if 'optics' in full_data:
                matched_star_file['optics'] = full_data['optics']
            matched_star_file['particles'] = matched_particles
            format_output_star(matched_star_file, output_path)
            
            self.logger.info(f"Successfully saved to: {output_path}")
            return output_path
            
        except FormatError as e:
            self.logger.error(f"Format error: {str(e)}")
            raise
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg)
