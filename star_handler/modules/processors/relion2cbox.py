from pathlib import Path

import subprocess
import random
import shutil
from typing import Optional, Tuple
import numpy as np
import os

from .base import BaseProcessor
from ...core.io import format_input_star
from ...core.transform import scale_coord, apply_shift
from ...core.selection import classify_star
from ...core.parallel import parallel_process_tomograms

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

        self.output_dir = Path('cryolo/3DTM_pre')
        self.all_tomos_link_dir = Path('cryolo/tomograms')
        self.isonet_dir = Path('isonet/corrected_tomos')
        
        self.coord_dir = self.output_dir / 'COORD_ori'
        self.coord_expanded_dir = self.output_dir / 'COORD_expanded'
        self.cbox_dir = self.output_dir / 'cbox_ori'
        self.cbox_expanded_dir = self.output_dir / 'cbox_expanded'
        self.sub_star_dir = self.output_dir / 'sub_folder'
    
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
        self.ensure_dir(self.output_dir, self.coord_dir, self.coord_expanded_dir, 
                        self.cbox_dir, self.cbox_expanded_dir)

        self._link_all_tomos()

        classify_star(self.star_file)
        source_sub_folder = Path('sub_folder')
        if source_sub_folder.exists() and source_sub_folder.is_dir():
            if self.sub_star_dir.exists():
                shutil.rmtree(self.sub_star_dir)
            shutil.move(str(source_sub_folder), str(self.sub_star_dir))
        
        sub_star_files = list(self.sub_star_dir.glob("*.star"))
        self.logger.info(f"Found {len(sub_star_files)} tomograms to process.")

        parallel_results = parallel_process_tomograms(
            sub_star_files,
            self._sub_star_to_COORD
        )

        self.logger.info("Converting to cbox...")
        cbox_success_count = 0
        successful_stems = []
        for result in parallel_results:
            if self._COORD_to_cbox(result):
                cbox_success_count += 1
                successful_stems.append(result['stem'])
        self.logger.info(f"Successfully processed {cbox_success_count} out of {len(sub_star_files)} files.")
        
        self._link_cbox_mrc(successful_stems)

    def _link_all_tomos(self):
        """
        Create symbolic links for ALL corrected tomograms from the isonet 
        directory into the central `cryolo/tomograms` directory.
        """
        self.ensure_dir(self.all_tomos_link_dir)
        self.logger.info(f"Linking all tomograms from {self.isonet_dir} to {self.all_tomos_link_dir}...")
        
        for tomo_source_path in self.isonet_dir.glob("*_corrected.mrc"):
            link_target_path = self.all_tomos_link_dir / f"{tomo_source_path.stem.replace('_corrected', '')}.mrc"

            if link_target_path.exists():
                continue

            try:
                relative_source = os.path.relpath(tomo_source_path, self.all_tomos_link_dir)
                os.symlink(relative_source, link_target_path)
            except Exception as e:
                self.logger.error(f"Failed to link {tomo_source_path.name}: {e}")
                        
    def _scale_shift(self, star_data: dict) -> Tuple[np.ndarray, int]:
        """Extract and process coordinates from star data.
        
        [PARAMETERS]
        star_data : dict
            Star file data containing particles and optics
            
        [OUTPUT]
        Tuple[np.ndarray, int]:
            - Processed coordinates array
            - Box size from optics
        """
        box_size = star_data['optics']['rlnImageSize'][0]
        
        if self.bin_factor != 1:
            star_data['particles'] = scale_coord(
                star_data['particles'],
                self.bin_factor,
                self.bin_factor,
                self.bin_factor
            )
        
        shift_result = apply_shift(star_data)
        coord = np.array(shift_result[0]).astype(int)
        return coord, box_size
        
    def _save_COORD(self, coord: np.ndarray, 
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
        
    def _COORD_to_cbox(self, result: dict) -> bool:
        """
        Manages the conversion process of a tomogram's coord files to cbox format.
        This includes checking for upstream errors from coordinate generation.

        [PARAMETERS]
        result : dict
            A dictionary from the parallel processing step containing file info.

        [OUTPUT]
        bool
            True if both conversions were successful, False otherwise.
        """
        if result.get('error'):
            self.logger.error(f"Failed to generate coordinates for {result['stem']}: {result['error']}")
            return False
            
        try:
            self._call_cryolo(result['coord_path'], result['box_size'])
            self._call_cryolo(result['expanded_coord_path'], result['box_size'], is_expanded=True)
            return True
        except Exception as e:
            self.logger.error(f"Failed to convert {result['stem']} to cbox: {e}")
            return False

    def _call_cryolo(self, coord_path: Path, box_size: int, is_expanded: bool = False):
        """Call cryolo_boxmanager_tools.py to convert a single coord file to cbox format."""
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

    def _sub_star_to_COORD(self, sub_star_file: Path) -> dict:
        """Generate coord files from a single sub star file.
        
        [PARAMETERS]
        sub_star_file : Path
            Path to sub STAR file
            
        [OUTPUT]
        dict:
            A dictionary containing processing results:
            - 'stem': str
            - 'box_size': int
            - 'coord_path': Path
            - 'expanded_coord_path': Path
            - 'error': Optional[str]
        """
        stem = sub_star_file.stem
        try:
            star = format_input_star(sub_star_file)
            coord, box_size = self._scale_shift(star)
            
            coord_path = self._save_COORD(coord, stem)
            
            expanded_coord = self._expand_z_coord(coord)
            expanded_coord_path = self._save_COORD(
                expanded_coord, 
                stem, 
                is_expanded=True
            )
            
            return {
                'stem': stem,
                'box_size': box_size,
                'coord_path': coord_path,
                'expanded_coord_path': expanded_coord_path,
                'error': None
            }
            
        except Exception as e:
            return {
                'stem': stem,
                'box_size': -1,
                'coord_path': None,
                'expanded_coord_path': None,
                'error': str(e)
            }

    def _link_cbox_mrc(self, successful_stems: list):
        """
        Create verification links for the two largest tomograms and their 
        corresponding CBOX files inside the `3DTM_pre` output directory.
        """
        if len(successful_stems) < 2:
            self.logger.info("Not enough successful files to create verification links.")
            return

        train_tomo_dir = self.output_dir / 'tomograms'
        train_cbox_dir = self.output_dir / 'CBOX'
        self.ensure_dir(train_tomo_dir, train_cbox_dir)

        try:
            sorted_stems = sorted(
                successful_stems,
                key=lambda s: (self.cbox_expanded_dir / f"{s}.cbox").stat().st_size,
                reverse=True
            )
            selected_files = sorted_stems[:2]
            
            for stem in selected_files:
                source_tomo_link = self.all_tomos_link_dir / f"{stem}.mrc"
                target_tomo_link = train_tomo_dir / f"{stem}.mrc"

                if not target_tomo_link.exists():
                    relative_tomo_source = os.path.relpath(source_tomo_link, train_tomo_dir)
                    os.symlink(relative_tomo_source, target_tomo_link)

                source_cbox_file = self.cbox_expanded_dir / f"{stem}.cbox"
                target_cbox_link = train_cbox_dir / f"{stem}.cbox"

                if not target_cbox_link.exists():
                    relative_cbox_source = os.path.relpath(source_cbox_file, train_cbox_dir)
                    os.symlink(relative_cbox_source, target_cbox_link)

            self.logger.info(f"Created verification links for: {', '.join(selected_files)}")

        except FileNotFoundError as e:
            self.logger.error(f"Error creating links: Could not find a required file. {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while creating links: {e}")
