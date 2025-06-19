"""
Provides a base class for all star_handler operations, handling common
setup for output directories and logging.
"""

from pathlib import Path
from typing import Union
from ..utils.logger import setup_logger

class StarHandlerBase:
    """Base class for all STAR file operations."""
    
    def __init__(self, output_dir: Union[str, Path] = 'analysis'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger(self.__class__.__name__)
    
    def save_results(self, data, name: str):
        """Save analysis results.
        To be implemented in subclasses."""
        raise NotImplementedError
        
    def plot_results(self, data, name: str):
        """Generate plots.
        To be implemented in subclasses."""
        raise NotImplementedError
