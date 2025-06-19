"""Base processor for star handler operations.

[Workflow]
1. Initialize with optional working directory
2. Set up logging
3. Validate input files
4. Process files with error handling
5. Generate output paths consistently

[PARAMETERS]
working_dir : str, optional
    Working directory for file operations (default: current directory)
    
[OUTPUT]
None

[RAISES]
FormatError
    If input file validation fails
ProcessingError
    If processing operations fail
ValidationError
    If input parameters are invalid

[EXAMPLE]
# Create a processor with custom working directory
processor = MyProcessor(working_dir="/path/to/work")
processor.process()
"""

from pathlib import Path
from typing import Union, Optional

from ...utils.errors import FormatError
from ...utils.logger import setup_logger

class BaseProcessor:
    """Base class for all star file processors.
    
    Provides common functionality for:
    - Logging
    - File validation
    - Output path handling
    - Directory creation
    """
    
    def __init__(self, working_dir: Optional[str] = None):
        """Initialize base processor.
        
        [PARAMETERS]
        working_dir : str, optional
            Working directory for file operations (default: current directory)
        """
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.logger = setup_logger(self.__class__.__name__.lower())
        
    def validate_files(self, *files: Union[str, Path]) -> None:
        """Validate existence of input files.
        
        [PARAMETERS]
        *files : Union[str, Path]
            Variable number of file paths to validate
            
        [RAISES]
        FormatError : If any file does not exist
        """
        for file in files:
            path = Path(file)
            if not path.exists():
                raise FormatError(f"File not found: {file}")
                
    def ensure_dir(self, *dirs: Union[str, Path]) -> None:
        """Ensure directories exist, create if needed.
        
        [PARAMETERS]
        *dirs : Union[str, Path]
            Variable number of directory paths to create
        """
        for dir_path in dirs:
            Path(dir_path).mkdir(exist_ok=True)
            
    def get_output_path(self, 
                       input_path: Union[str, Path],
                       suffix: str = '',
                       output_dir: Optional[Union[str, Path]] = None) -> Path:
        """Generate standardized output path.
        
        [PARAMETERS]
        input_path : Union[str, Path]
            Original input file path
        suffix : str, optional
            Suffix to add to filename (default: '')
        output_dir : Union[str, Path], optional
            Output directory (default: processor's working directory)
            
        [OUTPUT]
        Path : Generated output path
        """
        path = Path(input_path)
        out_dir = Path(output_dir) if output_dir else self.working_dir
        
        self.ensure_dir(out_dir)
        return out_dir / f"{path.stem}{suffix}{path.suffix}"
        
    def process(self) -> None:
        """Process files with standardized error handling.
        
        This is a placeholder that should be overridden by child classes.
        
        [RAISES]
        NotImplementedError : If child class doesn't implement process()
        """
        raise NotImplementedError("Child classes must implement process()")
