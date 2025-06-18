"""
Base class for STAR file analysis.

Implements a common workflow for particle analysis:
1. Read and preprocess STAR file
2. Split into sub-files by tomogram
3. Process each tomogram in parallel
4. Combine and visualize results
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform

from star_handler.core.star_handler import (
    format_input_star, format_output_star,
    scale_coord, m_to_rln, classify_star, apply_shift, 
    parallel_process_tomograms
)
from star_handler.utils.logger import setup_logger, log_execution

class AnalysisError(Exception):
    """Base exception for analysis errors."""
    pass

class Base:
    """Base class for all STAR file operations."""
    
    def __init__(self, output_dir: Union[str, Path] = 'analysis'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger(self.__class__.__name__)
    
    def save_results(self, data, name: str):
        """Save analysis results."""
        # To be implemented by subclasses
        raise NotImplementedError
        
    def plot_results(self, data, name: str):
        """Generate plots."""
        # To be implemented by subclasses
        raise NotImplementedError

class BaseAnalyzer(Base):
    """Base class for single STAR file analysis.
    
    [ATTRIBUTES]
    star_file : Path
        Input STAR file path
    config : AnalysisConfig
        Analysis configuration
    logger : logging.Logger
        Logger instance
    """
    
    ANALYSIS_TYPE: str = "base"

    
    def __init__(self, 
                 star_file: str,
                 output_dir: Union[str, Path] = 'analysis',
                 **config_params) -> None:
        """Initialize analyzer with input file and configuration.
        
        [PARAMETERS]
        star_file : str
            Path to input STAR file
        output_dir : Union[str, Path]
            Base output directory, defaults to 'analysis'
        **config_params : dict
            Configuration parameters to override defaults
        """
        super().__init__(output_dir=Path(output_dir) / self.ANALYSIS_TYPE)
        self.star_file = Path(star_file)
        if not self.star_file.exists():
            raise AnalysisError(f"STAR file not found: {star_file}")
            
        self.config = self._init_config(config_params)
        
        log_file = self.output_dir / f"{self.ANALYSIS_TYPE}_analysis.log"
        self.logger = setup_logger(
            f"{self.ANALYSIS_TYPE}_analyzer",
            str(log_file)
        )
        
        self.output_dirs = self._setup_output_dirs()

    def _init_config(self, config_params: dict) -> Any:
        """Initialize configuration from parameters.
        
        [PARAMETERS]
        config_params : dict
            Configuration parameters
            
        [OUTPUT]
        Any:
            Configuration class instance initialized with provided params
            
        [RAISES]
        AttributeError:
            If CONFIG_CLASS is not defined by subclass
        """
        if not hasattr(self, 'CONFIG_CLASS'):
            raise AttributeError(
                f"Analyzer {self.__class__.__name__} must define CONFIG_CLASS"
            )
            
        return self.CONFIG_CLASS(**config_params)
        
    def _setup_output_dirs(self) -> Dict[str, Path]:
        """Create output directory structure.
        
        [OUTPUT]
        Dict[str, Path]:
            Mapping of directory names to paths
        """
        dirs = {
            'data': self.output_dir / 'data',
            'plots': self.output_dir / 'plots', 
            'combined': self.output_dir / 'combined'
        }
        
        for dir_path in dirs.values():
            dir_path.mkdir(exist_ok=True)
            
        return dirs
        
    @log_execution
    def process(self) -> Dict[str, Any]:
        """Execute full analysis workflow.
        
        [WORKFLOW]
        1. Read and preprocess input, split into sub-files
        2. Process each tomogram
        3. Combine results
        4. Generate report

        [OUTPUT]
        Dict[str, Any]:
            Combined results from all tomograms
            
        [RAISES]
        AnalysisError:
            If any processing step fails
        """
        try:
            self.logger.info(f"Preparing input file: {self.star_file}")
            processed_star, sub_star_files = self.prepare_star_data()
            
            self.logger.info("Starting parallel tomogram processing")
            results = parallel_process_tomograms(
                sub_star_files,
                self._process_tomogram
            )
            
            self.logger.info("Combining results")
            combined_results = self._combine_results(results)
            
            self._generate_report(combined_results)
            
            self.logger.info(
                f"Analysis complete. Processed {len(sub_star_files)} tomograms"
            )
            return combined_results
            
        except Exception as e:
            raise AnalysisError(f"Analysis failed: {str(e)}")
            
    def prepare_star_data(self,
                         input_file: Optional[Union[str, Path]] = None,
                         output_file_name: str = 'processed.star',
                         sub_dir_name: str = 'sub_files') -> Tuple[Dict[str, pd.DataFrame], List[Path]]:
        """Process input STAR file and split by tomogram.
        
        This is a public interface that handles the initial data preparation steps
        common to all analyzers. It encapsulates the workflow of reading,
        processing, and splitting STAR files while managing output directories
        and intermediate files.
        
        [WORKFLOW]
        1. Read STAR file
        2. Handle format conversion (M to Relion)
        3. Scale coordinates by pixel size
        4. Split into sub-files by tomogram
        5. Filter sub-files by minimum particle count
        
        [PARAMETERS]
        input_file : Union[str, Path], optional
            Path to input STAR file, defaults to self.star_file if None
        output_file_name : str, optional
            Name for the processed output STAR file, defaults to 'processed.star'
        sub_dir_name : str, optional
            Name for the sub-directory containing split files, defaults to 'sub_files'
            
        [OUTPUT]
        Tuple[Dict[str, pd.DataFrame], List[Path]]:
            - Processed STAR data
            - Paths to generated sub-files
            
        [RAISES]
        AnalysisError:
            If processing or splitting fails
            
        [EXAMPLE]
            # Using default parameters
            star_data, sub_files = analyzer.prepare_star_data()
            
            # With custom parameters
            star_data, sub_files = analyzer.prepare_star_data(
                input_file='path/to/custom.star',
                output_file_name='my_processed.star',
                sub_dir_name='custom_splits'
            )
        """
        try:
            input_path = Path(input_file) if input_file else self.star_file
            star_data = format_input_star(input_path)
            _, star_data['particles'] = apply_shift(star_data)
            particles = star_data['particles']
            
            if particles.columns[0].startswith('wrp'):
                self.logger.info('Converting from M format')
                particles = m_to_rln(particles)
                star_data['particles'] = particles
            # M format pixel size is 1 by default

            if 'optics' in star_data:
                pixel_size = star_data['optics']['rlnImagePixelSize'].values[0]
                self.logger.info(f'Scaling coordinates by pixel size: {pixel_size}')
                particles = scale_coord(particles, pixel_size, pixel_size, pixel_size)
                star_data['particles'] = particles

            output_file = self.output_dir / output_file_name
            format_output_star(star_data, output_file)
            
            sub_dir = self.output_dir / sub_dir_name
            sub_files = classify_star(
                star_data,
                tag='rlnMicrographName',
                output_dir=sub_dir
            )
            
            filtered_sub_files = self._filter_by_particle_count(
                sub_files, 
                min_particles=3
            )
            
            return star_data, filtered_sub_files
            
        except Exception as e:
            raise AnalysisError(f"Failed to prepare STAR data: {str(e)}")
            
    def _filter_by_particle_count(self,
                                  sub_files: List[Path],
                                  min_particles: int = 3) -> List[Path]:
        """Filter sub-files by minimum particle count.
        
        [WORKFLOW]
        1. Read each sub-file to check particle count
        2. Skip files with insufficient particles
        3. Log skipped files for reporting
        
        [PARAMETERS]
        sub_files : List[Path]
            List of sub-file paths to filter
        min_particles : int, optional
            Minimum number of particles required, defaults to 3
            
        [OUTPUT]
        List[Path]:
            Filtered list of sub-files with sufficient particles
        """
        filtered_files = []
        skipped_files = []
        
        for sub_file in sub_files:
            try:
                data = format_input_star(sub_file)['particles']
                particle_count = len(data)
                
                if particle_count >= min_particles:
                    filtered_files.append(sub_file)
                else:
                    skipped_files.append(sub_file.stem)
                    self.logger.info(
                        f"Skipping {sub_file.stem}: only {particle_count} particles "
                        f"(minimum required: {min_particles})"
                    )
                    sub_file.unlink(missing_ok=True)
                    
            except Exception as e:
                self.logger.warning(
                    f"Error reading {sub_file}: {str(e)}. Skipping."
                )
                skipped_files.append(sub_file.stem)
                sub_file.unlink(missing_ok=True)
        
        if skipped_files:
            self.logger.info(
                f"Filtered out {len(skipped_files)} tomograms with insufficient particles: "
                f"{', '.join(skipped_files)}"
            )
        
        self.logger.info(
            f"Proceeding with {len(filtered_files)} tomograms "
            f"(filtered out {len(skipped_files)})"
        )
        
        return filtered_files
            
    def _process_tomogram(self,
                         star_file: Path) -> Tuple[str, Dict[str, Any]]:
        """Process a single tomogram.
        
        [WORKFLOW]
        1. Read tomogram data
        2. Calculate distances
        3. Perform analysis
        4. Save results
        
        [PARAMETERS]
        star_file : Path
            Tomogram STAR file
            
        [OUTPUT]
        Tuple[str, Dict[str, Any]]:
            Tomogram name and analysis results
            
        [RAISES]
        AnalysisError:
            If processing fails
        """
        try:
            tomogram = star_file.stem
            data = format_input_star(star_file)['particles']
            coords = data[[
                'rlnCoordinateX',
                'rlnCoordinateY',
                'rlnCoordinateZ'
            ]].values
            
            dist_matrix = squareform(pdist(coords))
            
            results = self._analyze(data, coords, dist_matrix)
            
            self._save_tomogram_results(tomogram, results)
            
            return tomogram, results
            
        except Exception as e:
            raise AnalysisError(
                f"Failed to process tomogram {star_file}: {str(e)}"
            )
            
    def _analyze(self,
                data: pd.DataFrame,
                coords: np.ndarray,
                dist_matrix: np.ndarray) -> Dict[str, Any]:
        """Perform specific analysis (must be implemented by subclasses).
        
        [PARAMETERS]
        data : pd.DataFrame
            Full particle data
        coords : np.ndarray
            Coordinate array (N, 3)
        dist_matrix : np.ndarray
            Distance matrix (N, N)
            
        [OUTPUT]
        Dict[str, Any]:
            Analysis results
            
        [RAISES]
        NotImplementedError:
            If not implemented by subclass
        """
        raise NotImplementedError
        
    def _save_tomogram_results(self,
                             tomogram: str,
                             results: Dict[str, Any]) -> None:
        """Save results for a tomogram (must be implemented by subclasses).
        
        [PARAMETERS]
        tomogram : str
            Tomogram identifier
        results : Dict[str, Any]
            Analysis results
            
        [RAISES]
        NotImplementedError:
            If not implemented by subclass
        """
        raise NotImplementedError
        
    def _combine_results(self,
                        results: List[Tuple[str, Dict[str, Any]]]
                        ) -> Dict[str, Any]:
        """Combine results from all tomograms (must be implemented by subclasses).
        
        [PARAMETERS]
        results : List[Tuple[str, Dict[str, Any]]]
            Results from each tomogram
            
        [OUTPUT]
        Dict[str, Any]:
            Combined statistics
            
        [RAISES]
        NotImplementedError:
            If not implemented by subclass
        """
        raise NotImplementedError
        
    def _save_data(self,
                  data: Union[pd.DataFrame, Dict[str, np.ndarray]],
                  filename: str,
                  prefix: str = 'data') -> Path:
        """Save analysis data to file.
        
        [PARAMETERS]
        data : Union[pd.DataFrame, Dict[str, np.ndarray]]
            Data to save
        filename : str 
            Output filename (without extension)
        prefix : str
            Directory prefix ('data' or 'combined')
            
        [OUTPUT]
        Path:
            Path to saved file
        """
        output_file = self.output_dirs[prefix] / f"{filename}.txt"
        
        if isinstance(data, pd.DataFrame):
            data.to_csv(output_file, sep='\t', index=False)
        else:
            pd.DataFrame(data).to_csv(output_file, sep='\t', index=False)
            
        return output_file
        
    def _write_report_section(self,
                            file,
                            title: str,
                            content: Dict[str, Any]) -> None:
        """Write a section to the report file.
        
        [PARAMETERS]
        file : TextIO
            Open file handle to write to
        title : str
            Section title
        content : Dict[str, Any]
            Key-value pairs to write as bullet points
        """
        file.write(f"=== {title} ===\n\n")
        for key, value in content.items():
            if isinstance(value, (int, float)):
                file.write(f"- {key}: {value:g}\n")
            else:
                file.write(f"- {key}: {value}\n")
        file.write("\n")
        
    def _generate_report(self, results: Dict[str, Any]) -> None:
        """Generate final report (must be implemented by subclasses).
        
        [PARAMETERS]
        results : Dict[str, Any]
            Combined results
            
        [RAISES]
        NotImplementedError:
            If not implemented by subclass
        """
        raise NotImplementedError

class BaseComparer(Base):
    """Base class for comparing two STAR files."""
    
    def __init__(self, file1: str, file2: str, **kwargs):
        super().__init__(**kwargs)
        self.file1 = Path(file1)
        self.file2 = Path(file2)
    
    def compare(self):
        """Execute comparison workflow."""
        raise NotImplementedError

class BaseTriComparer(Base):
    """Base class for comparing three STAR files."""
    
    def __init__(self, main_file: str, aux1_file: str, aux2_file: str, **kwargs):
        super().__init__(**kwargs)
        self.main_file = Path(main_file)
        self.aux1_file = Path(aux1_file)
        self.aux2_file = Path(aux2_file)
    
    def compare(self):
        """Execute triple comparison workflow."""
        raise NotImplementedError
