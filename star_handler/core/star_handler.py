"""
Core functionality for handling STAR files.

This module provides the fundamental operations for reading, writing,
and manipulating RELION STAR files. It supports both RELION 3.0 and 3.1
formats, as well as conversion from M (Warp) format.
"""

import os
from pathlib import Path
from typing import Dict, Union, List, Optional, Any, Tuple
from functools import wraps
from datetime import datetime

import starfile
import pandas as pd
import numpy as np
import requests

class StarFileError(Exception):
    """Base exception for STAR file handling errors."""
    pass

class FormatError(StarFileError):
    """Raised when there are issues with file format."""
    pass

class ProcessingError(StarFileError):
    """Raised when processing operations fail."""
    pass

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

def find_tomogram_name(particles: pd.DataFrame) -> pd.Series:
    """Extract unique tomogram names from particle data.
    
    [WORKFLOW]
    1. Access 'rlnMicrographName' column
    2. Get unique values
    
    [PARAMETERS]
    particles : pd.DataFrame
        Particle data containing micrograph information
        
    [OUTPUT]
    pd.Series
        Unique tomogram names
        
    [RAISES]
    ProcessingError
        If required column is missing
        
    [EXAMPLE]
    >>> tomogram_names = find_tomogram_name(particles_df)
    """
    try:
        if 'rlnMicrographName' not in particles.columns:
            raise ProcessingError("Missing 'rlnMicrographName' column")
        return particles['rlnMicrographName'].drop_duplicates()
    except Exception as e:
        raise ProcessingError(f"Failed to find tomogram names: {str(e)}")

def scale_coord(particles: pd.DataFrame,
                x: float,
                y: float,
                z: float) -> pd.DataFrame:
    """Scale particle coordinates by specified factors.
    
    [WORKFLOW]
    1. Validate input coordinates
    2. Apply scaling factors
    
    [PARAMETERS]
    particles : pd.DataFrame
        Particle data with coordinates
    x, y, z : float
        Scaling factors for each dimension
        
    [OUTPUT]
    pd.DataFrame
        DataFrame with scaled coordinates
        
    [RAISES]
    ProcessingError
        If coordinate columns are missing
        
    [EXAMPLE]
    >>> scaled_df = scale_coord(particles_df, 2.0, 2.0, 2.0)
    """
    required_cols = ['rlnCoordinateX', 'rlnCoordinateY', 'rlnCoordinateZ']
    try:
        if not all(col in particles.columns for col in required_cols):
            raise ProcessingError("Missing coordinate columns")
            
        scaled = particles.copy()
        scaled['rlnCoordinateX'] *= x
        scaled['rlnCoordinateY'] *= y
        scaled['rlnCoordinateZ'] *= z
        return scaled
    except Exception as e:
        raise ProcessingError(f"Failed to scale coordinates: {str(e)}")

def apply_shift(star: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Apply coordinate shifts from refinement.
    
    [WORKFLOW]
    1. Get pixel size from optics
    2. Convert shifts from Angstroms to pixels
    3. Apply to coordinates
    
    [PARAMETERS]
    star : Dict[str, pd.DataFrame]
        Star file data with optics and particles
        
    [OUTPUT]
    pd.DataFrame
        Shifted coordinates (X, Y, Z)
        
    [RAISES]
    ProcessingError
        If required data is missing
        
    [EXAMPLE]
    >>> shifted_coords = apply_shift(star_data)
    """
    try:
        if 'optics' not in star:
            raise ProcessingError("Missing optics data")
            
        pixel = star['optics']['rlnImagePixelSize'][0]
        p = star['particles']
        
        required_cols = [
            'rlnCoordinateX', 'rlnCoordinateY', 'rlnCoordinateZ',
            'rlnOriginXAngst', 'rlnOriginYAngst', 'rlnOriginZAngst'
        ]
        if not all(col in p.columns for col in required_cols):
            raise ProcessingError("Missing coordinate or shift columns")
            
        shifted = pd.DataFrame()
        shifted['rlnCoordinateX'] = p['rlnCoordinateX'] - p['rlnOriginXAngst']/pixel
        shifted['rlnCoordinateY'] = p['rlnCoordinateY'] - p['rlnOriginYAngst']/pixel
        shifted['rlnCoordinateZ'] = p['rlnCoordinateZ'] - p['rlnOriginZAngst']/pixel
        
        particles_shifted = p.copy()
        particles_shifted[['rlnCoordinateX', 'rlnCoordinateY', 'rlnCoordinateZ']] = shifted

        return shifted, particles_shifted
    except Exception as e:
        raise ProcessingError(f"Failed to apply shifts: {str(e)}")

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
        
def split_by_tomogram(star_data: Dict[str, pd.DataFrame],
                     output_dir: Path) -> List[Path]:
    """Split STAR data by tomogram.
    
    [PARAMETERS]
    star_data : Dict[str, pd.DataFrame]
        Processed STAR data
    output_dir : Path
        Directory to save sub-files
        
    [OUTPUT]
    List[Path]:
        Paths to generated sub-files
    
    [EXAMPLE]
    >>> split_by_tomogram(star_data, Path("sub_files"))
    """
    return classify_star(
        star_data,
        tag='rlnMicrographName',
        output_dir=output_dir
    )

def add_particle_names(particles: pd.DataFrame) -> pd.DataFrame:
    """Extract and add particle names from image names.
    
    [WORKFLOW]
    1. Extract base name from image path
    2. Remove suffix
    
    [PARAMETERS]
    particles : pd.DataFrame
        Particle data
        
    [OUTPUT]
    pd.DataFrame
        Data with added particle_name column
        
    [RAISES]
    ProcessingError
        If naming fails
        
    [EXAMPLE]
    >>> with_names = add_particle_names(particles_df)
    """
    try:
        if 'rlnImageName' not in particles.columns:
            raise ProcessingError("Missing rlnImageName column")
            
        result = particles.copy()
        result['particle_name'] = (
            result['rlnImageName']
            .str.split('/').str[-1]
            .str.rsplit('_', n=1).str[0]
        )
        return result
    except Exception as e:
        raise ProcessingError(f"Failed to add particle names: {str(e)}")

def parallel_process_tomograms(star_files: List[Union[str, Path]],
                             process_func: callable,
                             *args,
                             **kwargs) -> List[Tuple[str, Any]]:
    """Process multiple tomograms in parallel.
    
    [WORKFLOW]
    1. Setup processing pool
    2. Apply function to each file
    3. Collect results
    
    [PARAMETERS]
    star_files : List[Union[str, Path]]
        List of STAR files to process
    process_func : callable
        Processing function to apply
    *args, **kwargs
        Additional arguments for process_func
        
    [OUTPUT]
    List[Tuple[str, Any]]
        Processing results for each tomogram
        
    [RAISES]
    ProcessingError
        If parallel processing fails
        
    [EXAMPLE]
    >>> results = parallel_process_tomograms(files, process_func)
    """
    from multiprocessing import Pool, cpu_count
    
    try:
        n_cores = max(1, cpu_count() - 1)
        with Pool(n_cores) as pool:
            results = []
            for star_file in star_files:
                result = pool.apply_async(
                    process_func,
                    (star_file, *args),
                    kwargs
                )
                results.append(result)
            return [r.get() for r in results]
    except Exception as e:
        raise ProcessingError(f"Parallel processing failed: {str(e)}")

def merge_for_match(ref_particles: pd.DataFrame,
                   full_particles: pd.DataFrame,
                   merge_keys: List[str] = ['rlnOpticsGroup', 'particle_name'],
                   keep_unmatched: bool = False) -> pd.DataFrame:
    """Merge reference particles with full dataset.
    
    [WORKFLOW]
    1. Validate merge keys
    2. Perform merge operation
    3. Handle unmatched entries
    
    [PARAMETERS]
    ref_particles : pd.DataFrame
        Reference particles
    full_particles : pd.DataFrame
        Complete particle dataset
    merge_keys : List[str]
        Columns to merge on
    keep_unmatched : bool
        Whether to keep unmatched entries
        
    [OUTPUT]
    pd.DataFrame
        Merged particle data
        
    [RAISES]
    ProcessingError
        If merging fails
        
    [EXAMPLE]
    >>> merged = merge_for_match(ref_df, full_df)
    """
    try:
        for df, name in [(ref_particles, 'reference'),
                        (full_particles, 'full')]:
            missing = set(merge_keys) - set(df.columns)
            if missing:
                raise ProcessingError(
                    f"Missing merge keys in {name} dataset: {missing}"
                )
                
        merged = ref_particles.merge(
            full_particles,
            on=merge_keys,
            how='left' if keep_unmatched else 'inner',
            suffixes=('_ref', '_full')
        )
        
        merged = merged.drop_duplicates(subset=merge_keys)
        
        if keep_unmatched:
            unmatched = merged[merged['rlnImageName_full'].isna()]
            if not unmatched.empty:
                print(f"Warning: {len(unmatched)} unmatched particles")
                
        return merged
    except Exception as e:
        raise ProcessingError(f"Merging failed: {str(e)}")

def m_to_rln(particles: pd.DataFrame) -> pd.DataFrame:
    """Convert M (Warp) format to RELION format.
    
    [WORKFLOW]
    1. Rename wrp prefixes to rln
    2. Handle special cases
    
    [PARAMETERS]
    particles : pd.DataFrame
        M format particle data
        
    [OUTPUT]
    pd.DataFrame
        RELION format particle data
        
    [RAISES]
    ProcessingError
        If conversion fails
        
    [EXAMPLE]
    >>> relion_data = m_to_rln(warp_data)
    """
    try:
        wrp_cols = [col for col in particles.columns 
                    if col.startswith('wrp')]
        if not wrp_cols:
            raise ProcessingError("No Warp format columns found")
            
        result = particles.copy()
        rename_dict = {
            col: col.replace('wrp', 'rln').rstrip('1')
            for col in wrp_cols
        }
        rename_dict['wrpSourceName'] = 'rlnMicrographName'
        
        result.rename(columns=rename_dict, inplace=True)
        return result
    except Exception as e:
        raise ProcessingError(f"Format conversion failed: {str(e)}")

def notify_and_log(func: callable) -> callable:
    """Decorator for logging and notification.
    
    [WORKFLOW]
    1. Log usage to file
    2. Send Slack notification
    3. Execute function
    
    [PARAMETERS]
    func : callable
        Function to wrap
        
    [OUTPUT]
    callable
        Wrapped function
        
    [EXAMPLE]
    >>> @notify_and_log
    >>> def process_data():
    >>>     pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Logging
            log_file = "/data/Users/Siyu/Scripts/star_handler/script_usage.log"
            script_name = func.__name__
            user = os.getlogin()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            address = os.getcwd()
            
            with open(log_file, "a") as f:
                f.write(f"{script_name}\t{user}\t{timestamp}\t{address}\n")
                
            # Notification
            webhook_url = "https://hooks.slack.com/services/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"
            message = f"Script {script_name} used by: {user} at {timestamp} at {address}"
            response = requests.post(webhook_url, json={"text": message})
            
            if response.status_code != 200:
                print(f"Notification failed: {response.text}")
                
            return func(*args, **kwargs)
        except Exception as e:
            raise ProcessingError(f"Logging/notification failed: {str(e)}")
    return wrapper
