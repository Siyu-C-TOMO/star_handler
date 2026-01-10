"""
Core functionality for transforming and modifying particle data in STAR files.
"""
from typing import Dict, List
import pandas as pd

from ..utils.errors import ProcessingError

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

def merge_for_match(ref_particles: pd.DataFrame,
                   full_particles: pd.DataFrame,
                   merge_keys: List[str] = ['rlnOpticsGroup', 'particle_name'],
                   keep_unmatched: bool = False,
                   drop_duplicates: bool = True) -> pd.DataFrame:
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
        
        if drop_duplicates:
            merged = merged.drop_duplicates(subset=merge_keys)
        
        if keep_unmatched:
            unmatched = merged[merged[merge_keys[0]].isna()]
            if not unmatched.empty:
                print(f"Warning: {len(unmatched)} unmatched particles")
                print(unmatched.head(2).to_string())
                
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
