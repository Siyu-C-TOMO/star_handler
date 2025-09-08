import os
import re
import shutil
import logging
from pathlib import Path
from typing import Union, List, Dict
import pandas as pd
import xml.etree.ElementTree as ET

from .base import BaseProcessor
from ...core.io import format_input_star, format_output_star, run_command
from ...core import transform
from ...utils.errors import ProcessingError

class MCombineProcessor(BaseProcessor):
    """
    Automate the preparation and execution of an M processing pipeline.

    This processor reads a RELION star file to identify different datasets based on
    'rlnOpticsGroupName'. For each group, it finds the corresponding project
    directory, prepares the necessary files by renaming and modifying them with
    a prefix, and then runs a series of M-Tools commands to combine and process
    the datasets.

    The file preparation steps include:
    1.  Copying and renaming .tomostar files.
    2.  Copying and renaming .xml files from the warp_tiltseries directory.
    3.  Modifying the 'm_full.source' XML file to include the prefixed filenames.

    The M-pipeline execution is based on a standard 'm_combine.sh' script and
    includes creating a population, adding sources, creating masks and species,
    and running MCore for refinement.
    """

    def __init__(self, star_file: Union[str, Path], output_dir: Union[str, Path] = 'ribo_m', m_parameters: dict = None, skip_prepare: bool = False):
        """
        Initialize the processor.
        """
        super().__init__()
        self.star_file = Path(star_file).resolve()
        self.base_output_dir = Path(output_dir).resolve()
        self.work_dir = self.base_output_dir / "ribo_combine_after1and2"
        self.m_parameters = m_parameters if m_parameters else {}
        self.source_files_to_add = []
        self.modified_source_files = []
        self.skip_prepare = skip_prepare

    def _convert_star_to_m_format(self, star_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Converts a RELION star file to M format."""
        try:
            self.logger.info("Converting star file to M format...")
            
            pixel_size = star_data['optics']['rlnImagePixelSize'].iloc[0]
            _, particles_shifted = transform.apply_shift(star_data)
            scaled_df = transform.scale_coord(
                particles_shifted,
                x=pixel_size,
                y=pixel_size,
                z=pixel_size
            )
            
            new_data = pd.DataFrame()
            new_data['wrpCoordinateX1'] = scaled_df['rlnCoordinateX']
            new_data['wrpCoordinateY1'] = scaled_df['rlnCoordinateY']
            new_data['wrpCoordinateZ1'] = scaled_df['rlnCoordinateZ']
            new_data['wrpAngleRot1'] = scaled_df['rlnAngleRot']
            new_data['wrpAngleTilt1'] = scaled_df['rlnAngleTilt']
            new_data['wrpAnglePsi1'] = scaled_df['rlnAnglePsi']
            new_data['wrpRandomSubset'] = scaled_df['rlnRandomSubset']
            new_data['wrpSourceName'] = scaled_df['rlnTomoName']

            hash_map = self._get_hash_map()
            new_data['wrpSourceHash'] = scaled_df['rlnTomoName'].map(hash_map)

            self.logger.info("Successfully converted star file to M format.")
            return new_data

        except Exception as e:
            raise ProcessingError(f"Failed to convert star file to M format: {e}")

    def _get_hash_map(self):
        """Create a map of tomo names to hash values from all source files."""
        hash_map = {}
        for source_file in self.modified_source_files:
            try:
                tree = ET.parse(source_file)
                files = tree.find('Files')
                if files is not None:
                    for file_elem in files.findall('File'):
                        name = file_elem.get('Name')
                        hash_val = file_elem.get('Hash')
                        if name and hash_val:
                            hash_map[name] = hash_val
            except ET.ParseError as e:
                self.logger.error(f"Error parsing XML file {source_file}: {e}")
        return hash_map

    def run(self):
        """
        Run the full processing workflow.
        """
        self.logger.info(f"Starting M-Combine processing for {self.star_file}")
        
        star_data = format_input_star(self.star_file)
        if 'optics' not in star_data or 'particles' not in star_data:
            raise ValueError("Star file must contain optics and particles data.")

        if not self.skip_prepare:
            self.logger.info("Preparing files...")
            for _, row in star_data['optics'].iterrows():
                self._prepare_optic_group_files(row)
        else:
            self.logger.info("Skipping file preparation. Collecting existing source files...")
            self._collect_existing_source_files(star_data['optics'])

        if self.source_files_to_add:
            self.work_dir.mkdir(parents=True, exist_ok=True)
            m_format_df = self._convert_star_to_m_format(star_data)
            
            m_star_file_path = self.work_dir / "run_data_m.star"
            format_output_star({'particles': m_format_df}, m_star_file_path)
            self.logger.info(f"M-formatted star file saved to {m_star_file_path}")

            self._run_m_pipeline(m_star_file_path)
        else:
            self.logger.warning("No source files found or prepared. Skipping M pipeline.")

        self.logger.info("M-Combine processing finished.")

    def _prepare_optic_group_files(self, optics_row: pd.Series):
        """
        Prepare files for a single optics group entry.
        """
        optics_group_name = str(int(float(optics_row['rlnOpticsGroupName'])))
        project_dir = self._find_project_dir(optics_group_name)
        if not project_dir:
            self.logger.error(f"Could not find a project directory for group {optics_group_name}")
            return

        self._prepare_files(optics_group_name, project_dir)

    def _find_project_dir(self, prefix: str) -> Union[Path, None]:
        """
        Find the project directory in the current working directory based on the numeric prefix.
        """
        search_dir = Path.cwd()
        self.logger.info(f"Searching for project directory with prefix '{prefix}' in {search_dir}")
        for item in search_dir.iterdir():
            if item.is_dir() and item.name.startswith(prefix):
                self.logger.info(f"Found project directory: {item}")
                return item
        return None

    def _prepare_files(self, optics_group_name: str, project_dir: Path):
        """
        Copy and modify the necessary files for M processing.
        """
        tomostar_dir = project_dir / 'tomostar'
        if tomostar_dir.exists():
            for tomostar_file in tomostar_dir.glob('L*.tomostar'):
                new_name = f"{optics_group_name}_{tomostar_file.name}"
                shutil.copy2(tomostar_file, tomostar_dir / new_name)
                self.logger.debug(f"Copied {tomostar_file} to {new_name}")

        warp_dir = project_dir / 'warp_tiltseries'
        if warp_dir.exists():
            for xml_file in warp_dir.glob('L*.xml'):
                new_name = f"{optics_group_name}_{xml_file.name}"
                shutil.copy2(xml_file, warp_dir / new_name)
                self.logger.debug(f"Copied {xml_file} to {new_name}")

        source_file = warp_dir / 'm_full.source'
        if source_file.exists():
            self.source_files_to_add.append(source_file.resolve())
            self._modify_source_file(source_file, optics_group_name, project_dir)

    def _modify_source_file(self, source_file: Path, optics_group_name: str, project_dir: Path):
        """
        Add prefix to the file names inside the m_full.source XML file for backup.
        """
        try:
            tree = ET.parse(source_file)
            root = tree.getroot()
            
            files_element = root.find('Files')
            if files_element is None:
                self.logger.error(f"No 'Files' element found in {source_file}")
                return

            for file_element in files_element.findall('File'):
                original_name = file_element.get('Name')
                if original_name:
                    new_name = f"{optics_group_name}_{original_name}"
                    file_element.set('Name', new_name)
            
            output_source_file = source_file.parent / f"{optics_group_name}_withPrefix.source"
            tree.write(output_source_file, encoding='utf-8', xml_declaration=True)
            self.logger.info(f"Created backup source file: {output_source_file}")
            self.modified_source_files.append(output_source_file.resolve())

        except ET.ParseError as e:
            self.logger.error(f"Error parsing XML file {source_file}: {e}")

    def _run_m_pipeline(self, m_star_file: Path):
        """
        Execute the M processing pipeline in the output directory.
        """
        self.logger.info(f"Running M pipeline in: {self.work_dir}")
        self.work_dir.mkdir(parents=True, exist_ok=True)

        name = self.m_parameters.get("name", "combine")
        species = self.m_parameters.get("species", "ribosome")
        job_dir_str = self.m_parameters.get("job_dir")
        if not job_dir_str:
            self.logger.error("job_dir not provided in m_parameters.")
            return
        job_dir = Path(job_dir_str).resolve()
        
        population_file = self.work_dir / f"{name}.population"

        commands = []

        commands.append(
            ["MTools", "create_population", "--directory", str(self.work_dir), "--name", name]
        )

        for source_path in self.source_files_to_add:
            commands.append(
                ["MTools", "add_source", "--population", str(population_file), "--source", str(source_path)]
            )

        mask_output = self.work_dir / "mask.mrc"
        commands.append(
            ["relion_mask_create", "--i", str(job_dir / "run_class001.mrc"), "--o", str(mask_output), "--ini_threshold", "0.025"]
        )
    
        commands.append(
            ["MTools", "create_species",
             "--population", str(population_file),
             "--name", species,
             "--diameter", "350",
             "--sym", "C1",
             "--temporal_samples", "1",
             "--half1", str(job_dir / "run_half1_class001_unfil.mrc"),
             "--half2", str(job_dir / "run_half2_class001_unfil.mrc"),
             "--mask", str(mask_output),
             "--particles_m", str(m_star_file),
             "--angpix_resample", "1.87",
             "--lowpass", "20"]
        )

        mcore_common_args = ["--population", str(population_file)]
        mcore_refine_args = ["--refine_imagewarp", "6x4", "--refine_particles", "--ctf_defocus"]
        mcore_resource_args = ["--perdevice_refine", "4", "--perdevice_preprocess", "1", "--perdevice_postprocess", "1"]

        commands.extend([
            ["MCore", *mcore_common_args, *mcore_resource_args, "--iter", "0"],
            # ["MCore", *mcore_common_args, *mcore_refine_args, *mcore_resource_args, "--refine_tiltmovies"],
            ["MCore", *mcore_common_args, *mcore_refine_args, *mcore_resource_args, "--ctf_defocusexhaustive"],
            ["MCore", *mcore_common_args, *mcore_refine_args, *mcore_resource_args],
            ["MCore", *mcore_common_args, *mcore_refine_args, *mcore_resource_args, "--refine_stageangles"],
            # ["MCore", *mcore_common_args, *mcore_refine_args, *mcore_resource_args, "--refine_mag", "--ctf_cs", "--ctf_zernike3"],
            ["EstimateWeights", "--population", str(population_file), "--source", name, "--resolve_items"],
            ["MCore", *mcore_common_args, *mcore_resource_args],
            # ["EstimateWeights", "--population", str(population_file), "--source", name, "--resolve_frames"],
            # ["MCore", *mcore_common_args, *mcore_resource_args, "--refine_particles"],
            # ["MTools", "resample_trajectories", "--population", str(population_file), "--species", str(self.work_dir / "species*" / f"{species}.species"), "--samples", "2"],
            # ["MCore", *mcore_common_args, *mcore_resource_args, "--refine_stageangles", "--refine_mag", "--ctf_cs", "--ctf_zernike3"]
        ])

        for index, cmd in enumerate(commands):
            log_name = f"command{index}_{cmd[0]}.log"
            log_path = self.work_dir / "logs" / log_name
            
            module_to_load = "warp/2.0.0dev34"
            self.logger.info(f"Running command: {' '.join(cmd)}")
            run_command(cmd, log_path, cwd=self.work_dir, module_load=module_to_load)

        self.logger.info(f"M pipeline finished.")

    def _collect_existing_source_files(self, optics_df: pd.DataFrame):
        """
        Collect paths to already prepared source files.
        """
        for _, row in optics_df.iterrows():
            optics_group_name = str(int(float(row['rlnOpticsGroupName'])))
            project_dir = self._find_project_dir(optics_group_name)
            if not project_dir:
                self.logger.warning(f"Could not find project directory for group {optics_group_name}. Cannot collect source file.")
                continue
            
            source_file = (project_dir / 'warp_tiltseries' / 'm_full.source').resolve()
            if source_file.exists():
                self.source_files_to_add.append(source_file)
                self.logger.info(f"Found original source file: {source_file}")
                self._modify_source_file(source_file, optics_group_name, project_dir)
            else:
                self.logger.warning(f"Expected source file not found: {source_file}")
