from typing import Optional, List, Tuple, Dict, Any

from .base import BaseProcessor
from ..utils.errors import FormatError, ProcessingError
from ..core.star_handler import (
    format_input_star, format_output_star,
    scale_coord, threshold_star,
    parallel_process_tomograms
)

class TemplateMatch3DProcessor(BaseProcessor):
    """
    Process 3D template matching results for visualization and filtering.
    
    [WORKFLOW]
    1. Check for ../../ribo_list_final.txt:
       If not exists:
       - Generate ../../ribo_list_blank.txt with star prefixes
       - Scale coordinates and save to /scaled for Napari
       If exists:
       - Filter particles based on criteria and save to /filtered

    [PARAMETERS]
    working_dir : str, optional
        Working directory containing star files (default: current directory)

    [OUTPUT]
    When no ribo_list.txt:
    - ../../ribo_list_blank.txt: One column file with star prefixes
    - scaled/*.star: Scaled coordinates for Napari visualization

    When ribo_list_final.txt exists:
    - filtered/*.star: Cleaned particles based on:
      [star_prefix] [low_z] [high_z] [cc_threshold]

    [EXAMPLE]
    # In matching directory:
    $ star-handler process-template-match-3D

    # Or specify directory:
    $ star-handler process-template-match-3D -d /path/to/matching
    """
    
    SCALE_FACTORS = (512, 720, 376)
    
    def __init__(self, working_dir: Optional[str] = None):
        """Initialize processor with optional working directory.
        
        [PARAMETERS]
        working_dir : str, optional
            Path to directory containing star files (default: current directory)
        """
        super().__init__(working_dir)
        self.list_file = self.working_dir.parent.parent / "ribo_list_final.txt"
        self.blank_list = self.working_dir.parent.parent / "ribo_list_blank.txt"
        
        self.scaled_dir = self.working_dir / "scaled"
        self.filtered_dir = self.working_dir / "filtered"
        
    def process(self) -> None:
        """Execute main processing workflow.
        
        - If ribo_list.txt exists: Clean particles based on criteria
        - If not: Generate blank list and prepare for visualization
        """
        if self.list_file.exists():
            self._clean_with_list()
        else:
            self._generate_blank_list()
            self._prepare_for_napari()
            
    def _generate_blank_list(self) -> None:
        """Generate ribo_list_blank.txt with star prefixes.
        
        Creates a file with one prefix per line (e.g. L8_G1_ts_017) extracted
        from star filenames in the working directory.
        
        [RAISES]
        ValueError: If no STAR files found in directory
        """
        star_files = list(self.working_dir.glob("*.star"))
        if not star_files:
            raise ValueError("No STAR files found in directory")
            
        prefixes = []
        for star in star_files:
            parts = star.stem.split('_')
            prefix = '_'.join(parts[:4])
            prefixes.append(prefix)
            
        with open(self.blank_list, 'w') as f:
            for prefix in sorted(set(prefixes)):
                f.write(f"{prefix}\n")
                
        self.logger.info(f"Generated {self.blank_list}")
        
    def _process_single_for_napari(self, star_file) -> Tuple[str, Optional[str]]:
        """Process a single STAR file for Napari visualization.
        
        [PARAMETERS]
        star_file : Path
            Path to STAR file to process
            
        [OUTPUT]
        Tuple[str, Optional[str]]:
            (filename, error_message if any)
        """
        try:
            star_data = format_input_star(star_file)
            star_data['particles'] = scale_coord(
                star_data['particles'],
                *self.SCALE_FACTORS
            )
            
            output_path = self.scaled_dir / star_file.name
            format_output_star(star_data, output_path)
            return star_file.name, None
            
        except Exception as e:
            return star_file.name, str(e)

    def _prepare_for_napari(self) -> None:
        """Scale coordinates for visualization in Napari.
        
        Reads all star files in working directory, scales coordinates,
        and saves results to /scaled directory using parallel processing.
        """
        self.scaled_dir.mkdir(exist_ok=True)
        star_files = list(self.working_dir.glob("*.star"))
        
        if not star_files:
            raise ValueError("No STAR files found in directory")
            
        results = parallel_process_tomograms(
            star_files,
            self._process_single_for_napari
        )
        
        for filename, error in results:
            if error:
                self.logger.error(f"Failed to process {filename}: {error}")
            else:
                self.logger.info(f"Processed {filename}")
                
    def _process_single_with_list(self, params: Tuple[str, float, float, float]) -> Tuple[str, Optional[str]]:
        """Process a single entry from ribo_list.txt
        
        [PARAMETERS]
        params : Tuple[str, float, float, float]
            (prefix, low_z, high_z, cc) parameters for processing
            
        [OUTPUT]
        Tuple[str, Optional[str]]:
            (prefix, error_message if any)
        """
        prefix, low_z, high_z, cc = params
        
        try:
            star_file = next(self.scaled_dir.glob(f"{prefix}*.star"))
            star_data = format_input_star(star_file)
            
            particles = star_data['particles']
            particles = threshold_star(
                particles,
                'rlnAutopickFigureOfMerit',
                min_val=cc
            )
            particles = threshold_star(
                particles,
                'rlnCoordinateZ',
                min_val=low_z,
                max_val=high_z
            )
            star_data['particles'] = particles
            
            particles['rlnMicrographName'] = particles['rlnMicrographName'].str.replace(
                '.mrc', '.tomostar'
            )

            output_path = self.filtered_dir / f"{prefix}.star"
            format_output_star(star_data, output_path)
            return prefix, None
            
        except Exception as e:
            return prefix, str(e)

    def _clean_with_list(self) -> None:
        """Clean particles based on criteria from ribo_list.txt.
        
        Reads criteria from ribo_list.txt and applies thresholds:
        - Figure of merit (cc_threshold)
        - Z coordinate range (low_z to high_z)
        
        Results are saved to /filtered directory using parallel processing.
        """
        self.filtered_dir.mkdir(exist_ok=True)
        
        # Read and parse all parameters first
        params_list = []
        with open(self.list_file, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 4:
                    self.logger.error(f"Invalid line format: {line.strip()}")
                    continue
                    
                prefix = parts[0]
                try:
                    low_z, high_z, cc = map(float, parts[1:])
                    params_list.append((prefix, low_z, high_z, cc))
                except ValueError as e:
                    self.logger.error(f"Invalid numeric values in line: {line.strip()}")
                    continue
        
        if not params_list:
            raise ValueError("No valid entries found in ribo_list.txt")
            
        results = parallel_process_tomograms(
            params_list,
            self._process_single_with_list
        )
        
        for prefix, error in results:
            if error:
                self.logger.warning(f"Failed to process {prefix}: {error}")
            else:
                self.logger.info(f"Processed {prefix}")
