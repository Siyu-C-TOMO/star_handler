from pathlib import Path
from typing import Union

from .base import BaseProcessor
from ..utils.errors import FormatError, ProcessingError
from ..core.star_handler import (
    format_input_star,
    format_output_star,
    add_particle_names,
    merge_for_match
)

class FilterByRefProcessor(BaseProcessor):
    """Filter particles in STAR file based on a reference STAR file.
    
    [WORKFLOW]
    1. Check if input STAR files exist and are valid
    2. Read and format both reference and full STAR files
    3. Add particle names to both datasets for matching
    4. Match particles based on optics group and particle name
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
    Basic usage:
        $ star-handler process-filter-by-ref -f particles.star -r reference.star
    
    Custom output directory:
        $ star-handler process-filter-by-ref -f particles.star -r reference.star -o filtered_results
    """
  
    def __init__(self, full_star: str, ref_star: str, output_dir: str = 'matched'):
        """Initialize processor with full and ref star file paths.

        [PARAMETERS]
        full_star : str
            Path to the full star file to be filtered
        ref_star : str
            Path to the reference star file
        output_dir : str, optional
            Directory to save output files (default: 'matched')
            
        [RAISES]
        FormatError
            If either full_star or ref_star file does not exist
        """
        super().__init__()
        self.validate_files(full_star, ref_star)
        
        self.full_star = full_star
        self.ref_star = ref_star
        self.output_dir = output_dir
        
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
        required_cols = ['rlnOpticsGroup']
        for col in required_cols:
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
            
            self.logger.info("Processing particle data...")
            full_particles_with_name = add_particle_names(full_data['particles'])
            ref_particles_with_name = add_particle_names(ref_data['particles'])
            ref_particles_selector = ref_particles_with_name[['rlnOpticsGroup',
                                                            'particle_name']]

            self.logger.info("Matching particles...")
            matched_particles = merge_for_match(
                ref_particles=ref_particles_selector,
                full_particles=full_particles_with_name,
                merge_keys=['rlnOpticsGroup', 'particle_name'],
                keep_unmatched=False
            )
            
            self.logger.info(f"Found {len(matched_particles)} matching particles")

            output_path = self.get_output_path(
                self.full_star, 
                '_matched',
                self.output_dir
            )
            
            matched_star_file = {
                'optics': full_data['optics'],
                'particles': matched_particles[full_data['particles'].columns]
            }
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
