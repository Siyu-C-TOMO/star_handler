from pathlib import Path
from typing import Union

from .base import BaseProcessor
from ...utils.errors import FormatError, ProcessingError
from ...core.io import format_input_star, format_output_star
from ...core.transform import add_particle_names, merge_for_match

class FilterByRefProcessor(BaseProcessor):
    """Filter particles in STAR file based on a reference STAR file.

    [WORKFLOW]
    1. Check if input STAR files exist and are valid
    2. Read and format both reference and full STAR files
    3. Add particle names to both datasets for matching
    4. Match particles based on optics group and particle name
    5. Save matched particles to output star file
    6. Optionally save unmatched particles to a remainder star file

    [PARAMETERS]
    full_star : str
        Path to STAR file to be filtered
    ref_star : str
        Path to reference STAR file
    output_dir : str, optional
        Output directory for results
    save_remainder : bool, optional
        Whether to also save unmatched particles to a _remainder.star file

    [OUTPUT]
    - Filtered STAR file in output directory
    - File named as original_name_matched.star
    - If save_remainder is True: original_name_remainder.star with unmatched particles

    [EXAMPLE]
    Basic usage:
        $ star-handler process-filter-by-match -f particles.star -r reference.star

    Custom output directory:
        $ star-handler process-filter-by-match -f particles.star -r reference.star -o filtered_results

    Save remainder:
        $ star-handler process-filter-by-match -f particles.star -r reference.star --save-remainder
    """

    def __init__(self, full_star: str, ref_star: str, output_dir: str = 'matched',
                 save_remainder: bool = False):
        """Initialize processor with full and ref star file paths.

        [PARAMETERS]
        full_star : str
            Path to the full star file to be filtered
        ref_star : str
            Path to the reference star file
        output_dir : str, optional
            Directory to save output files (default: 'matched')
        save_remainder : bool, optional
            Whether to also save unmatched particles (default: False)

        [RAISES]
        FormatError
            If either full_star or ref_star file does not exist
        """
        super().__init__()
        self.validate_files(full_star, ref_star)

        self.full_star = full_star
        self.ref_star = ref_star
        self.output_dir = output_dir
        self.save_remainder = save_remainder
        
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

            matched_star_file = {}
            if 'optics' in full_data:
                matched_star_file['optics'] = full_data['optics']
            matched_star_file['particles'] = matched_particles[full_data['particles'].columns]
            format_output_star(matched_star_file, output_path)

            self.logger.info(f"Successfully saved matched to: {output_path}")

            if self.save_remainder:
                all_merged = full_particles_with_name.merge(
                    ref_particles_selector,
                    on=['rlnOpticsGroup', 'particle_name'],
                    how='left',
                    indicator=True
                )
                remainder_particles = (
                    all_merged[all_merged['_merge'] == 'left_only']
                    .drop(columns=['_merge'])
                )
                self.logger.info(f"Found {len(remainder_particles)} remainder particles")

                remainder_path = self.get_output_path(
                    self.full_star,
                    '_remainder',
                    self.output_dir
                )
                remainder_star_file = {}
                if 'optics' in full_data:
                    remainder_star_file['optics'] = full_data['optics']
                remainder_star_file['particles'] = remainder_particles[full_data['particles'].columns]
                format_output_star(remainder_star_file, remainder_path)

                self.logger.info(f"Successfully saved remainder to: {remainder_path}")

            return output_path
            
        except FormatError as e:
            self.logger.error(f"Format error: {str(e)}")
            raise
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg)
