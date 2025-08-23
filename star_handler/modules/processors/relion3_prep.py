import shutil
from pathlib import Path
import pandas as pd

from .base_combiner import BaseRelionCombiner
from ...core.io import format_input_star, format_output_star, run_command

class Relion3PrepProcessor(BaseRelionCombiner):
    """
    Prepare and combine datasets for RELION 3.
    """

    def process_dataset(self, star_entry: pd.Series, output_angpix: float):
        """
        Run the full processing workflow for a single RELION 3 dataset entry.
        """
        self._setup_context(star_entry, output_angpix, relion_version=3)
        
        extracted_star_path = self._extract_particle(
            star_entry,
            output_angpix,
            dimension='3d',
            force_float32=True
        )
        
        self._process_outputs(extracted_star_path)
        self.processed_stars.append(extracted_star_path)

    def _process_outputs(self, star_path: Path):
        """
        Run post-extraction steps for RELION 3: rename folder and modify STAR file.
        """
        self._rename_subtomo_folder()
        self._add_prefix_to_star_file(star_path)

    def _rename_subtomo_folder(self):
        """Rename the subtomo directory with the dataset prefix."""
        source_dir = self.output_dir / "subtomo"
        target_dir = self.output_dir / f"{self.prefix}_subtomo"
        if source_dir.exists() and source_dir.is_dir():
            if target_dir.exists():
                self.logger.warning(f"Target directory {target_dir} already exists. Skipping rename.")
                return
            shutil.move(str(source_dir), str(target_dir))
            self.logger.info(f"Renamed '{source_dir.name}' to '{target_dir.name}'")
        else:
            self.logger.warning(f"Directory not found, skipping rename: {source_dir}")

    def _add_prefix_to_star_file(self, star_path: Path):
        """Add dataset prefix to specified columns in the STAR file."""
        if not star_path.exists():
            self.logger.warning(f"STAR file not found, skipping modification: {star_path}")
            return

        self.logger.info(f"Adding prefix to columns in {star_path.name}")
        star_data = format_input_star(star_path)
        
        data_block_key = next((key for key in star_data if isinstance(star_data[key], pd.DataFrame)), None)
        if not data_block_key:
            self.logger.warning(f"No data block found in {star_path.name}. Skipping modification.")
            return
            
        df = star_data[data_block_key]
        cols_to_prefix = ['rlnMicrographName', 'rlnImageName', 'rlnCtfImage']
        for col in cols_to_prefix:
            if col in df.columns:
                df[col] = self.prefix + '_' + df[col].astype(str)
        
        star_data[data_block_key] = df
        format_output_star(star_data, star_path)
        self.logger.info("Successfully added prefixes.")

    def combine_stars(self):
        """
        Combine all processed STAR files and fix the optics group information.
        """
        if not self.processed_stars:
            self.logger.warning("No STAR files to combine.")
            return

        self.logger.info(f"Combining {len(self.processed_stars)} STAR files...")
        
        output_star_path = self.output_dir / f"{self.combine_prefix}.star"
        
        input_files_str = '"' + " ".join([str(p) for p in self.processed_stars]) + '"'
        
        cmd = (
            f"relion_star_handler --combine --i {input_files_str} "
            f"--check_duplicates rlnImageName --o {output_star_path}"
        )
        
        log_path = self.output_dir / "logs" / "combine.log"
        run_command(cmd, log_path, cwd=self.output_dir, shell=True)
        
        self.logger.info(f"Successfully combined STAR files into {output_star_path}")
        
        self._fix_combined_optics(output_star_path)

    def _fix_combined_optics(self, star_path: Path):
        """
        Fix the optics group information in the combined STAR file.
        """
        self.logger.info(f"Fixing optics groups in {star_path.name}...")
        star_data = format_input_star(star_path)

        if 'optics' not in star_data or 'particles' not in star_data:
            self.logger.error("Combined star file is missing 'optics' or 'particles' data blocks.")
            return

        particles_df = star_data['particles']
        
        prefixes = particles_df['rlnImageName'].str.extract(r'(^\d+_)').iloc[:, 0].str.rstrip('_').unique()
        
        optics_template = star_data['optics'].iloc[0]
        new_optics_list = []
        prefix_to_id_map = {}
        for i, prefix in enumerate(prefixes):
            new_optics_group_id = i + 1
            prefix_to_id_map[prefix] = new_optics_group_id
            
            new_row = optics_template.copy()
            new_row['rlnOpticsGroup'] = new_optics_group_id
            new_row['rlnOpticsGroupName'] = prefix
            new_optics_list.append(new_row)
            
        new_optics_df = pd.DataFrame(new_optics_list)
        
        particle_prefixes = particles_df['rlnImageName'].str.extract(r'(^\d+_)').iloc[:, 0].str.rstrip('_')
        particles_df['rlnOpticsGroup'] = particle_prefixes.map(prefix_to_id_map)
        
        corrected_star_data = {'optics': new_optics_df, 'particles': particles_df}
        format_output_star(corrected_star_data, star_path)
        
        self.logger.info("Successfully fixed optics groups.")
