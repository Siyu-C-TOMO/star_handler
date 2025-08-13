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

    This function writes all data blocks from the input dictionary to the
    output STAR file, ensuring compatibility with various STAR file formats,
    including multi-block files from RELION 5.

    [WORKFLOW]
    1. Validate that the input is a non-empty dictionary.
    2. Write all key-value pairs from the dictionary to the STAR file.

    [PARAMETERS]
    star_file : Dict[str, pd.DataFrame]
        Dictionary containing data blocks to be written.
    file_name : Union[str, Path]
        Output file path.

    [RAISES]
    StarFileError
        If writing fails or the input dictionary is empty.

    [EXAMPLE]
    >>> data = {'particles': particles_df, 'optics': optics_df}
    >>> format_output_star(data, 'output.star')
    """
    try:
        if not star_file:
            raise FormatError("Input dictionary is empty. Nothing to write.")

        starfile.write(star_file, file_name, overwrite=True)
    except Exception as e:
        raise StarFileError(f"Failed to write STAR file: {str(e)}")
