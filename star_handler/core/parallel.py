"""
Core functionality for parallel processing.
"""
from typing import List, Union, Tuple, Any
from pathlib import Path
from multiprocessing import Pool, cpu_count

from ..utils.errors import ProcessingError

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
