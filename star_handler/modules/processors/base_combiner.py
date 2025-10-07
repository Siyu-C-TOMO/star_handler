import os
import re
from pathlib import Path
from typing import Union
import pandas as pd

from .base import BaseProcessor
from ...core.io import run_command

class BaseRelionCombiner(BaseProcessor):
    """
    Base processor for preparing and combining datasets for RELION.
    """

    def __init__(self,
                 output_dir: Union[str, Path] = '.',
                 combine_prefix: str = 'combine'):
        """
        Initialize the base processor.
        """
        super().__init__()
        self.base_output_dir = Path(output_dir).resolve()
        self.combine_prefix = combine_prefix
        
        self.prefix = ""
        self.output_dir = None
        self.project_dir = None
        self.processed_stars = []

    def _setup_context(self, star_entry: pd.Series, output_angpix: float, relion_version: int):
        """
        Set up paths and prefix for the current dataset.
        """
        project_dir = Path(star_entry['rlnStarAddress']).parts[0]
        
        match = re.match(r'^\d+', Path(project_dir).name)
        if not match:
            raise ValueError(f"Could not extract a numeric prefix from directory name: {Path(project_dir).name}")
        self.prefix = match.group(0)

        angpix_str = str(output_angpix).replace('.', 'p')
        self.output_dir = self.base_output_dir / f"relion{relion_version}_{angpix_str}A"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.project_dir = Path(project_dir)

    def _extract_particle(self, star_entry: pd.Series, output_angpix: float, dimension: str, force_float32: bool):
        """
        Run WarpTools ts_export_particles for a single entry.
        """
        input_star = Path(star_entry['rlnStarAddress']).resolve()
        
        self.logger.info(f"Processing project: {self.project_dir.name} with prefix {self.prefix}")

        output_star_path = (self.output_dir / f"{self.prefix}.star").resolve()
        
        env = os.environ.copy()
        if force_float32:
            env['WARP_FORCE_MRC_FLOAT32'] = '1'
            
        cmd = [
            "WarpTools", "ts_export_particles",
            "--settings", "warp_tiltseries.settings",
            "--input_star", str(input_star),
            "--input_processing", "warp_tiltseries",
            "--coords_angpix", str(star_entry['rlnPixelSize']),
            "--output_star", str(output_star_path),
            "--output_angpix", str(output_angpix),
            "--output_processing", str(self.output_dir.resolve()),
            "--box", "144",
            "--diameter", "350",
            "--relative_output_paths",
            "--device_list", "2",
            "--perdevice", "4",
            f"--{dimension}"
        ]
        
        log_path = self.output_dir / "logs" / f"{self.prefix}_extraction.log"
        run_command(cmd, log_path, cwd=self.project_dir, env=env, module_load="warp/2.0.0dev34")
        
        self.logger.info(f"Particle extraction completed for {self.prefix}.")
        return output_star_path
