"""
Base classes for comparing two or more STAR files.
"""

from pathlib import Path
from ...core.common_flow import StarHandlerBase

class BaseComparer(StarHandlerBase):
    """Base class for comparing two STAR files."""
    
    def __init__(self, file1: str, file2: str, **kwargs):
        super().__init__(**kwargs)
        self.file1 = Path(file1)
        self.file2 = Path(file2)
    
    def compare(self):
        """Execute comparison workflow."""
        raise NotImplementedError

class BaseTriComparer(StarHandlerBase):
    """Base class for comparing three STAR files."""
    
    def __init__(self, main_file: str, aux1_file: str, aux2_file: str, **kwargs):
        super().__init__(**kwargs)
        self.main_file = Path(main_file)
        self.aux1_file = Path(aux1_file)
        self.aux2_file = Path(aux2_file)
    
    def compare(self):
        """Execute triple comparison workflow."""
        raise NotImplementedError
