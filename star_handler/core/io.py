"""
Core I/O functionality for handling STAR files.
"""
from pathlib import Path
from typing import Dict, Union
import pandas as pd
import starfile

from ..utils.errors import StarFileError, FormatError

def format_input_star(file_name: Union[str, Path]) -> Dict[str, pd.DataFrame]:
    """Read and format a STAR file.
    
    [WORKFLOW]
    1. Read STAR file using starfile library
    2. Handle both RELION 3.0 and 3.1 formats
    3. Convert empty key to 'particles' for 3.0 format
    
    [PARAMETERS]
    file_name : Union[str, Path]
        Path to the STAR file
        
    [OUTPUT]
    Dict[str, pd.DataFrame]
        Dictionary containing 'particles' DataFrame and optionally 'optics'
        
    [RAISES]
    StarFileError
        If file cannot be read or has invalid format
        
    [EXAMPLE]
    >>> star_data = format_input_star('run_data.star')
    >>> particles_df = star_data['particles']
    """
    try:
        star_file = starfile.read(file_name, always_dict=True)
        if '' in star_file:
            star_file['particles'] = star_file.pop('')
        return star_file
    except Exception as e:
        raise FormatError(f"Failed to read STAR file: {str(e)}")

def format_output_star(star_file: Dict[str, pd.DataFrame], 
                      file_name: Union[str, Path]) -> None:
    """Write formatted data to a STAR file.
    
    [WORKFLOW]
    1. Check format (3.0 vs 3.1 based on presence of optics)
    2. Write appropriate format STAR file
    
    [PARAMETERS]
    star_file : Dict[str, pd.DataFrame]
        Dictionary containing particle data and optionally optics
    file_name : Union[str, Path]
        Output file path
        
    [RAISES]
    StarFileError
        If writing fails or input data is invalid
        
    [EXAMPLE]
    >>> format_output_star({'particles': particles_df}, 'output.star')
    """
    try:
        if 'particles' not in star_file:
            raise FormatError("Missing 'particles' data")
            
        if 'optics' in star_file:
            output_data = {
                'optics': star_file['optics'],
                'particles': star_file['particles']
            }
        else:
            output_data = {'particles': star_file['particles']}
            
        starfile.write(output_data, file_name)
    except Exception as e:
        raise StarFileError(f"Failed to write STAR file: {str(e)}")
