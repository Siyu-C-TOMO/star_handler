from pathlib import Path
from typing import Union

from .base import BaseProcessor
from ..utils.errors import FormatError, ProcessingError
from ..core.io import format_input_star, format_output_star

class ConditionalModifyProcessor(BaseProcessor):
    """
    Modify STAR file based on column condition.
    
    [WORKFLOW]
    1. Read STAR file
    2. Find particles matching condition
    3. Modify specified column values
    4. Save modified STAR file

    [PARAMETERS]
    star_file : str
        Path to STAR file
    condition : str
        Value to match
    string : str
        String to prepend
    column_ref : str
        Column to check
    column_to_modify : str
        Column to modify
    output_dir : str
        Output directory

    [OUTPUT]
    Modified STAR file with "_modified" suffix

    [EXAMPLE]
    Add prefix to micrograph names for optics group 1:
        $ star-handler star-modify-conditional -f particles.star -c 1 -s "micrographs/"
    """
    
    def __init__(self, 
                star_file: Union[str, Path],
                condition: str,
                value: str,
                column_ref: str = "rlnOpticsGroup",
                column_to_modify: str = "rlnMicrographName",
                output_dir: str = "modified"):
        """Initialize processor with file and modification parameters."""
        super().__init__()
        self.validate_files(star_file)
        
        self.star_file = Path(star_file)
        self.condition = condition
        self.value = value
        self.column_ref = column_ref
        self.column_to_modify = column_to_modify
        self.output_dir = Path(output_dir)
        
    def process(self) -> Path:
        """Execute modification workflow.
        
        [RAISES]
        FormatError
            If required columns are missing
        ProcessingError
            If modification fails
        """
        try:
            self.logger.info(f"Reading STAR file: {self.star_file}")
            star_data = format_input_star(self.star_file)
            particles = star_data['particles']
            
            if self.column_ref not in particles.columns:
                raise FormatError(f"Reference column not found: {self.column_ref}")
            if self.column_to_modify not in particles.columns:
                raise FormatError(f"Target column not found: {self.column_to_modify}")
            
            particles[self.column_ref] = particles[self.column_ref].astype(str)
            condition_met = particles[self.column_ref] == self.condition
            
            if not condition_met.any():
                self.logger.warning(
                    f"No particles matched condition: {self.column_ref} == {self.condition}"
                )
            else:
                particles.loc[condition_met, self.column_to_modify] = (
                    self.value + particles.loc[condition_met, self.column_to_modify]
                )
                self.logger.info(f"Modified {condition_met.sum()} particles")
            
            star_data['particles'] = particles
            output_path = self.get_output_path(
                self.star_file,
                '_modified',
                self.output_dir
            )
            format_output_star(star_data, output_path)
            
            self.logger.info(f"Saved to: {output_path}")
            return output_path
            
        except Exception as e:
            error_msg = f"Modification failed: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg)
