from pathlib import Path

import subprocess
import random
from typing import Optional, Tuple
import numpy as np
import os

from .base import BaseProcessor
from ..core.io import format_input_star
from ..core.transform import scale_coord, apply_shift
from ..core.selection import classify_star
from ..core.parallel import parallel_process_tomograms

class Relion2CboxProcessor(BaseProcessor):
    """
    Process STAR files from RELION to generate cryolo cbox files.

    [WORKFLOW]
    1. Create COORD directory for intermediate coord files
    2. Create sub_folder directory and classify star files by tomogram
    3. For each sub star file:
       - Scale coordinates if bin_factor > 1
       - Extract and shift coordinates
       - Generate .coord files in COORD/
       - Use cryolo tools to create .cbox files

    [PARAMETERS]
    star_file : Union[str, Path]
        RELION STAR file to process
    bin_factor : int, optional
        Scale factor for unbinning coordinates (default: 1)

    [OUTPUT]
    - COORD/*.coord: Original coordinate files for each tomogram
    - cbox_all/*.cbox: Original cryolo box files

    [EXAMPLE]
    $ star-handler process-relion2cbox -f /data/relion/Refine3D/run_data.star
    """
    
    def __init__(self, star_file: str, bin_factor: int = 1):
        """Initialize processor with input file and bin factor.
        
        [PARAMETERS]
        star_file : str
            Path to input STAR file
        bin_factor : int, optional
            Scale factor for unbinning coordinates (default: 1)
            
        [RAISES]
        FormatError
            If star file does not exist
        """
        super().__init__()
        self.validate_files(star_file)
        self.star_file = star_file
        self.bin_factor = bin_factor
        self.coord_dir = self.get_output_path('COORD', '_ori', 'COORD')
        self.coord_expanded_dir = self.get_output_path('COORD', '_expanded', 'COORD')
        self.cbox_dir = self.get_output_path('cbox', '_ori', 'cbox')
        self.cbox_expanded_dir = self.get_output_path('cbox', '_expanded', 'cbox')
    
    def _expand_z_coord(self, coord: np.ndarray) -> np.ndarray:
        """Expand Z coordinates to nearest multiples of 10.
        
        For each Z coordinate, generate one or two new coordinates:
        - If Z is already a multiple of 10, keep it unchanged
        - Otherwise, generate two points at the nearest lower and upper multiples of 10
        
        [PARAMETERS]
        coord : np.ndarray
            Input coordinates array (N x 3)
            
        [OUTPUT]
        np.ndarray
            Expanded coordinates array with Z values at multiples of 10
        """
        if not isinstance(coord, np.ndarray):
            coord = np.array(coord)
        if coord.ndim != 2 or coord.shape[1] != 3:
            raise ValueError("Input coordinates must be an Nx3 array")
            
        result = []
        z_coords = coord[:, -1]
        max_z = z_coords.max()
        
        for point in coord:
            x, y, z = point
            lower = (z // 10) * 10  
            upper = ((z + 9) // 10) * 10
            
            if lower == upper:
                result.append([x, y, lower])
            else:
                if 0 <= lower <= max_z:
                    result.append([x, y, lower])
                if 0 <= upper <= max_z:
                    result.append([x, y, upper])
                    
        return np.array(result)

    def process(self) -> None:
        """Execute main processing workflow.
        
        [RAISES]
        ProcessingError
            If any processing step fails
        """
        self.ensure_dir(self.coord_dir, self.coord_expanded_dir, 
                        self.cbox_dir, self.cbox_expanded_dir)
        
        classify_star(self.star_file)
        
        sub_star_files = list(Path('sub_folder').glob("*.star"))
        results = parallel_process_tomograms(
            sub_star_files,
            self._process_sub_star
        )

        error_count = 0
        success_count = 0
        for filename, error in results:
            if error:
                self.logger.error(f"Failed to process {filename}: {error}")
                error_count += 1
            else:
                self.logger.info(f"Processed {filename}")
                success_count += 1
        self.logger.info(f"Processed {success_count} files with {error_count} errors.")
        if error_count > 0:
            self.logger.warning("Some files failed to process. Check logs for details.")
                
        successful_files = [f for f, err in results if not err]
        if len(successful_files) >= 2:
            selected_files = random.sample(successful_files, 2)
            
            self.ensure_dir('tomograms', 'CBOX')
            
            for stem in selected_files:
                tomogram_link = Path('tomograms') / f"{stem}.mrc"
                if not tomogram_link.exists():
                    os.symlink(
                        f"../../isonet/tomograms/{stem}.mrc",
                        tomogram_link
                    )
                
                cbox_link = Path('CBOX') / f"{stem}.cbox"
                if not cbox_link.exists():
                    os.symlink(
                        f"../{self.cbox_expanded_dir}/{stem}.cbox",
                        cbox_link
                    )
            self.logger.info(f"Created symbolic links for: {', '.join(selected_files)}")
                
    def _extract_coordinates(self, star_data: dict) -> Tuple[np.ndarray, int]:
        """Extract and process coordinates from star data.
        
        [PARAMETERS]
        star_data : dict
            Star file data containing particles and optics
            
        [OUTPUT]
        Tuple[np.ndarray, int]:
            - Processed coordinates array
            - Box size from optics
        """
        box = star_data['optics']['rlnImageSize'][0]
        
        if self.bin_factor != 1:
            star_data['particles'] = scale_coord(
                star_data['particles'],
                self.bin_factor,
                self.bin_factor,
                self.bin_factor
            )
        
        shift_result = apply_shift(star_data)
        coord = np.array(shift_result[0]).astype(int)
        return coord, box
        
    def _save_coordinates(self, coord: np.ndarray, 
                         stem: str, 
                         is_expanded: bool = False) -> Path:
        """Save coordinates to file.
        
        [PARAMETERS]
        coord : np.ndarray
            Coordinate array to save
        stem : str
            Base name for output file
        is_expanded : bool
            Whether these are expanded coordinates
            
        [OUTPUT]
        Path
            Path to saved coordinate file
        """
        output_dir = self.coord_expanded_dir if is_expanded else self.coord_dir
        coord_path = output_dir / f"{stem}.coord"
        np.savetxt(coord_path, coord, delimiter='\t', fmt='%s')
        return coord_path
        
    def _convert_to_cbox(self, coord_path: Path, box_size: int, is_expanded: bool = False):
        """Convert coordinates to cbox format.
        
        [PARAMETERS]
        coord_path : Path
            Path to coordinate file
        box_size : int
            Box size for cryolo
        is_expanded : bool
            Whether to use expanded output directory
        """
        output_dir = self.cbox_expanded_dir if is_expanded else self.cbox_dir
        subprocess.run(
            [
                'cryolo_boxmanager_tools.py',
                'coords2cbox',
                '-i', str(coord_path),
                '-b', str(box_size),
                '-o', output_dir
            ],
            check=True
        )

    def _process_sub_star(self, sub_star_file: Path) -> Tuple[str, Optional[str]]:
        """Process single sub star file to generate coord and cbox.
        
        [PARAMETERS]
        sub_star_file : Path
            Path to sub STAR file
            
        [OUTPUT]
        Tuple[str, Optional[str]]:
            (filename, error_message if any)
        """
        try:
            star = format_input_star(sub_star_file)
            coord, box = self._extract_coordinates(star)
            
            coord_path = self._save_coordinates(coord, sub_star_file.stem)
            self._convert_to_cbox(coord_path, box)
            
            expanded_coord = self._expand_z_coord(coord)
            expanded_coord_path = self._save_coordinates(
                expanded_coord, 
                sub_star_file.stem, 
                is_expanded=True
            )
            self._convert_to_cbox(expanded_coord_path, box, is_expanded=True)
            
            return sub_star_file.stem, None
            
        except Exception as e:
            return sub_star_file.stem, str(e)
