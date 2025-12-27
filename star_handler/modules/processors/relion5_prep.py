import shutil
from pathlib import Path
from typing import Union, Dict
import pandas as pd

from .base_combiner import BaseRelionCombiner
from ...core.io import format_input_star, format_output_star

class Relion5PrepProcessor(BaseRelionCombiner):
    """
    Prepare and merge datasets for RELION 5.
    """

    def __init__(self,
                 output_dir: Union[str, Path] = 'ribo_relion',
                 combine_prefix: str = 'combine'):
        """
        Initialize the processor.
        """
        super().__init__(output_dir=output_dir, combine_prefix=combine_prefix)
        
        self.tomograms_star_path = None
        self.particles_star_path = None
        self.optimization_path = None
        self.particle_series_dir = None

    def process_dataset(self, star_entry: pd.Series, output_angpix: float):
        """
        Run the full processing workflow for a single RELION 5 dataset entry.
        """
        self._setup_context(star_entry, output_angpix, relion_version=5)
        
        self._extract_particle(
            star_entry,
            output_angpix,
            dimension='2d',
            force_float32=False
        )
        
        self._finalize_processing()

    def _finalize_processing(self):
        """
        Execute the post-extraction workflow for RELION 5.
        """
        self.logger.info(f"Finalizing processing for prefix: {self.prefix}")

        self.tomograms_star_path = self.output_dir / f"{self.prefix}_tomograms.star"
        self.particles_star_path = self.output_dir / f"{self.prefix}.star"
        self.optimization_path = self.output_dir / f"{self.prefix}_optimization_set.star"
        self.particle_series_dir = self.output_dir / "particleseries"

        self._backup_files()
        self._rename_particle_series()
        modified_tomograms_data = self._process_tomograms_star()     
        modified_particles_data, new_optics_group_id = self._process_particles_star()
        self._merge_stars(modified_tomograms_data, modified_particles_data, new_optics_group_id)
        self._create_optimization_set()

        self.logger.info(f"Workflow for {self.prefix} completed successfully.")

    def _backup_files(self):
        """Backup original files."""
        backup_dir = self.output_dir / 'backup_star'
        backup_dir.mkdir(exist_ok=True)
        self.logger.info(f"Backing up files to {backup_dir}")

        files_to_backup = [
            self.tomograms_star_path,
            self.particles_star_path,
            self.optimization_path,
            self.output_dir / f"{self.combine_prefix}.star",
            self.output_dir / f"{self.combine_prefix}_tomograms.star",
            self.output_dir / f"{self.combine_prefix}_optimisation_set.star"
        ]

        for file_path in files_to_backup:
            if file_path.exists():
                try:
                    shutil.copy(file_path, backup_dir)
                    self.logger.info(f"Backed up {file_path}")
                except Exception as e:
                    self.logger.warning(f"Could not back up {file_path}: {e}")

    def _rename_particle_series(self):
        """Rename the particle series directory."""
        source_psd = self.output_dir / "particleseries"
        new_name = self.output_dir / f"{self.prefix}_particleseries"
        if source_psd.exists() and source_psd.is_dir():
            if new_name.exists():
                self.logger.warning(f"Target directory {new_name} already exists. Skipping rename.")
                return
            shutil.move(str(source_psd), str(new_name))
            self.logger.info(f"Renamed '{source_psd.name}' to '{new_name.name}'")
        else:
            self.logger.warning(f"Directory not found, skipping rename: {source_psd}")
    
    @staticmethod
    def _needs_prefix(series: pd.Series, prefix: str) -> bool:
        """Return True if this column requires prefix (all non-digit-starting)."""
        starts = series.str.match(r'\d', na=False)

        if starts.nunique() > 1:
            raise ValueError(f"Mixed format in {series.name}: some start with digit, some do not.")

        return not starts.iloc[0]

    def _process_tomograms_star(self) -> Dict[str, pd.DataFrame]:
        """Process the tomograms STAR file."""
        if not self.tomograms_star_path.exists():
            self.logger.warning(f"Tomograms star file not found: {self.tomograms_star_path}. Skipping.")
            return {}
        self.logger.info(f"Processing tomograms file: {self.tomograms_star_path}")
        tomo_data = format_input_star(self.tomograms_star_path)
        
        processed_data = {}
        for key, df in tomo_data.items():
            add_prefix = False
            if 'rlnTomoName' in df.columns:
                add_prefix = self._needs_prefix(df['rlnTomoName'], self.prefix)
                if add_prefix:
                    df['rlnTomoName'] = f"{self.prefix}_" + df['rlnTomoName'].astype(str)

            if 'rlnOpticsGroupName' in df.columns:
                df['rlnOpticsGroupName'] = self.prefix

            new_key = (
                f"{self.prefix}_{key}"
                if add_prefix and key.endswith('.tomostar')
                else key
            )
            processed_data[new_key] = df

        format_output_star(processed_data, self.output_dir / f"{self.prefix}_tomograms.star")
        return processed_data

    def _process_particles_star(self):
        """Process the particles STAR file."""
        if not self.particles_star_path.exists():
            self.logger.warning(f"Particles star file not found: {self.particles_star_path}. Skipping.")
            return {}, -1
        self.logger.info(f"Processing particles file: {self.particles_star_path}")
        particle_data = format_input_star(self.particles_star_path)

        if 'optics' in particle_data:
            optics_df = particle_data['optics'].head(1).copy()
            optics_df['rlnOpticsGroupName'] = self.prefix
            particle_data['optics'] = optics_df
            self.logger.info("Processed optics data: kept first row and set rlnOpticsGroupName.")
        
        combine_star_path = self.output_dir / f"{self.combine_prefix}.star"
        new_optics_group_id = 1
        if combine_star_path.exists():
            try:
                combine_data = format_input_star(combine_star_path)
                if 'optics' in combine_data and not combine_data['optics'].empty:
                    new_optics_group_id = combine_data['optics']['rlnOpticsGroup'].max() + 1
            except Exception as e:
                self.logger.warning(f"Could not read existing combine.star to determine optics group ID: {e}")
        
        if 'optics' in particle_data:
            particle_data['optics']['rlnOpticsGroup'] = new_optics_group_id

        if 'particles' in particle_data:
            particles_df = particle_data['particles']
            if 'rlnImageName' in particles_df.columns:
                particles_df['rlnImageName'] = f"{self.prefix}_" + particles_df['rlnImageName'].astype(str)

            cols_numeric_logic = ['rlnTomoName', 'rlnTomoParticleName']
            for col in cols_numeric_logic:
                if col in particles_df.columns:
                    if self._needs_prefix(particles_df[col], self.prefix):
                        particles_df[col] = f"{self.prefix}_" + particles_df[col].astype(str)

            particles_df['rlnOpticsGroup'] = new_optics_group_id
            particle_data['particles'] = particles_df
            self.logger.info("Processed particles data: added prefixes and set rlnOpticsGroup.")

        format_output_star(particle_data, self.output_dir / f"{self.prefix}.star")
        return particle_data, new_optics_group_id

    def _merge_stars(self, tomograms_data: Dict[str, pd.DataFrame], particles_data: Dict[str, pd.DataFrame], new_optics_group_id: int):
        """Merge the processed STAR files into combined files."""
        if not particles_data:
            self.logger.warning("No particles data available for merging.")
            return
        self.logger.info("Merging STAR files...")

        combine_star_path = self.output_dir / f"{self.combine_prefix}.star"
        if combine_star_path.exists():
            self.logger.info(f"Found existing {combine_star_path}, merging...")
            try:
                combined_particles_data = format_input_star(combine_star_path)
            except Exception as e:
                self.logger.warning(f"Could not read existing {combine_star_path}, creating a new one. Error: {e}")
                combined_particles_data = {}
        else:
            self.logger.info(f"No existing {combine_star_path}, creating new one.")
            combined_particles_data = {}

        for key, new_df in particles_data.items():
            if key in ['optics', 'particles']:
                if key not in combined_particles_data:
                    combined_particles_data[key] = pd.DataFrame()
                combined_particles_data[key] = pd.concat(
                    [combined_particles_data.get(key, pd.DataFrame()), new_df],
                    ignore_index=True
                )
            else:
                combined_particles_data[key] = new_df
        
        format_output_star(combined_particles_data, combine_star_path)
        self.logger.info(f"Successfully merged and saved to {combine_star_path}")

        combine_tomo_path = self.output_dir / f"{self.combine_prefix}_tomograms.star"
        if combine_tomo_path.exists():
            self.logger.info(f"Found existing {combine_tomo_path}, merging...")
            try:
                combined_tomo_data = format_input_star(combine_tomo_path)
            except Exception as e:
                self.logger.warning(f"Could not read existing {combine_tomo_path}, creating a new one. Error: {e}")
                combined_tomo_data = {}
        else:
            self.logger.info(f"No existing {combine_tomo_path}, creating new one.")
            combined_tomo_data = {}
        
        for key, new_df in tomograms_data.items():
            if key == 'global':
                if 'global' not in combined_tomo_data:
                    combined_tomo_data['global'] = pd.DataFrame()
                combined_tomo_data['global'] = pd.concat(
                    [combined_tomo_data.get('global', pd.DataFrame()), new_df],
                    ignore_index=True
                )
            else:
                combined_tomo_data[key] = new_df

        format_output_star(combined_tomo_data, combine_tomo_path)
        self.logger.info(f"Successfully merged and saved to {combine_tomo_path}")

    def _create_optimization_set(self):
        """Create the combine_optimization_set.star file if it doesn't exist."""
        opt_set_path = self.output_dir / f"{self.combine_prefix}_optimisation_set.star"
        if not opt_set_path.exists():
            self.logger.info(f"Creating new optimisation set file: {opt_set_path}")
            
            particles_file = f"{self.combine_prefix}.star"
            tomograms_file = f"{self.combine_prefix}_tomograms.star"

            content = (
                "data_\n\n"
                f"_rlnTomoParticlesFile   {particles_file}\n"
                f"_rlnTomoTomogramsFile   {tomograms_file}\n"
            )
            
            try:
                with open(opt_set_path, 'w') as f:
                    f.write(content)
                self.logger.info(f"Successfully created {opt_set_path}")
            except Exception as e:
                self.logger.error(f"Failed to create optimisation set file: {e}")
        else:
            self.logger.info(f"{opt_set_path} already exists, skipping creation.")
