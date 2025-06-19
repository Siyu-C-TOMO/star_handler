"""
Core functionality for selecting and splitting particles from STAR files.
"""
from pathlib import Path
from typing import Dict, Union, List, Optional
import pandas as pd

from .io import format_input_star, format_output_star
from ..utils.errors import ProcessingError

def threshold_star(particles: pd.DataFrame,
                  tag: str,
                  min_val: float = float('-inf'),
                  max_val: float = float('inf')) -> pd.DataFrame:
    """Filter particles based on value thresholds.
    
    [WORKFLOW]
    1. Validate input tag exists
    2. Apply threshold filters
    
    [PARAMETERS]
    particles : pd.DataFrame
        Particle data
    tag : str
        Column name to filter on
    min_val : float
        Minimum threshold value
    max_val : float
        Maximum threshold value
        
    [OUTPUT]
    pd.DataFrame
        Filtered particle data
        
    [RAISES]
    ProcessingError
        If tag is missing or filtering fails
        
    [EXAMPLE]
    >>> filtered = threshold_star(particles_df, 'rlnDefocusU', min_val=1000)
    """
    try:
        if tag not in particles.columns:
            raise ProcessingError(f"Missing column: {tag}")
            
        return particles[
            (particles[tag] >= min_val) & 
            (particles[tag] <= max_val)
        ]
    except Exception as e:
        raise ProcessingError(f"Failed to apply threshold: {str(e)}")

def classify_star(
    star_data: Union[Dict[str, pd.DataFrame], str, Path],
    tag: str = 'rlnMicrographName',
    partial_match: int = -1,
    output_dir: Optional[Path] = None
) -> List[Path]:
    """Classify STAR data based on metadata tag values.
    
    [WORKFLOW]
    1. Validate input data
    2. Extract unique values from specified tag
    3. Create classified sub-files
    
    [PARAMETERS]
    star_data : Union[Dict[str, pd.DataFrame], str, Path]
        STAR data dictionary or path to STAR file
    tag : str
        Metadata tag for classification (default: rlnMicrographName)
    partial_match : int
        Number of parts to match in tag value (-1 for full match)
    output_dir : Optional[Path]
        Output directory (defaults to 'sub_folder')
        
    [OUTPUT]
    List[Path]:
        Paths to generated sub-files
        
    [RAISES]
    ProcessingError:
        If classification fails
        
    [EXAMPLE]
    >>> classify_star(star_data, tag='rlnClassNumber', partial_match=2)
    """
    try:
        if isinstance(star_data, (str, Path)):
            star_data = format_input_star(star_data)
        
        particles = star_data['particles']
        if tag not in particles.columns:
            raise ProcessingError(f"Tag {tag} not found in STAR file")
            
        output_dir = Path(output_dir or 'sub_folder')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if partial_match > 0:
            values = particles[tag].apply(
                lambda x: '/'.join(str(x).split('/')[:partial_match])
            ).unique()
        else:
            values = particles[tag].unique()
            
        sub_files = []
        for value in values:
            if partial_match > 0:
                subset = particles[
                    particles[tag].apply(
                        lambda x: '/'.join(str(x).split('/')[:partial_match])
                    ) == value
                ]
            else:
                subset = particles[particles[tag] == value]
                
            if isinstance(value, str):
                output_name = value.replace('/', '_').split('.')[0]
            else:
                output_name = str(value)
                
            sub_file = output_dir / f"{output_name}.star"
            star_data['particles'] = subset
            format_output_star(star_data, sub_file)
            sub_files.append(sub_file)
            
        return sub_files
        
    except Exception as e:
        raise ProcessingError(f"Failed to classify STAR file: {str(e)}")

def split_star_by_threshold(
    star_file_path: Union[str, Path],
    tag: str,
    thresholds: Union[float, List[float]],
    output_dir: Optional[Union[str, Path]] = None
) -> List[Path]:
    """
    Split a STAR file into multiple files based on value thresholds for a given tag.

    [Workflow]
    1. Read the input STAR file.
    2. Validate the thresholds and sort them.
    3. Define value ranges based on the thresholds.
    4. For each range, filter particles using the `threshold_star` function.
    5. Save each filtered subset into a new STAR file in the output directory.

    [PARAMETER]
    star_file_path : Union[str, Path]
        Path to the input STAR file.
    tag : str
        The column name (tag) in the particle data to apply the threshold on.
    thresholds : Union[float, List[float]]
        A single threshold value (float) or a list of threshold values (list of floats).
        - If a single float, splits into two files: <= threshold and > threshold.
        - If a list of floats, splits into multiple files representing ranges.
    output_dir : Optional[Union[str, Path]], optional
        Directory to save the output STAR files. If None, a directory named
        'threshold_split' will be created in the same directory as the input file.
        Defaults to None.

    [OUTPUT]
    List[Path]
        A list of Path objects pointing to the created STAR files.

    [RAISES]
    ProcessingError
        If the specified tag doesn't exist or if any processing step fails.
    ValueError
        If the `thresholds` parameter is invalid.

    [EXAMPLE]
    # Split by a single threshold
    >>> split_star_by_threshold('data.star', 'rlnAngleTilt', 45.0)

    # Split into three ranges: <=30, >30 and <=60, >60
    >>> split_star_by_threshold('data.star', 'rlnDefocusU', [30, 60])
    """
    try:
        star_file_path = Path(star_file_path)
        star_data = format_input_star(star_file_path)
        particles = star_data['particles']

        if tag not in particles.columns:
            raise ProcessingError(f"Tag '{tag}' not found in STAR file.")

        if output_dir is None:
            output_dir = star_file_path.parent / 'threshold_split'
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(thresholds, (int, float)):
            thresholds = [thresholds]
        elif not isinstance(thresholds, list) or not all(isinstance(t, (int, float)) for t in thresholds):
            raise ValueError("`thresholds` must be a float or a list of floats.")
        
        sorted_thresholds = sorted(thresholds)
        
        ranges = []
        ranges.append({'max': sorted_thresholds[0], 'name': f'le_{sorted_thresholds[0]}'})
        
        for i in range(len(sorted_thresholds) - 1):
            min_val = sorted_thresholds[i]
            max_val = sorted_thresholds[i+1]
            ranges.append({'min': min_val, 'max': max_val, 'name': f'gt_{min_val}_le_{max_val}'})

        ranges.append({'min': sorted_thresholds[-1], 'name': f'gt_{sorted_thresholds[-1]}'})

        output_files = []
        for r in ranges:
            min_val = r.get('min', float('-inf'))
            max_val = r.get('max', float('inf'))
            
            if min_val == max_val and 'min' in r and 'max' in r:
                continue

            if 'min' in r: # greater than or equal to
                subset = particles[particles[tag] > min_val]
            else: # less than or equal to
                subset = particles[particles[tag] <= max_val]

            if 'max' in r and 'min' in r:
                 subset = particles[(particles[tag] > min_val) & (particles[tag] <= max_val)]
            
            if not subset.empty:
                output_name = f"{star_file_path.stem}_{tag}_{r['name']}.star"
                output_path = output_dir / output_name
                
                new_star_data = star_data.copy()
                new_star_data['particles'] = subset
                format_output_star(new_star_data, output_path)
                output_files.append(output_path)
                
        return output_files

    except Exception as e:
        raise ProcessingError(f"Failed to split STAR file by threshold: {str(e)}")
