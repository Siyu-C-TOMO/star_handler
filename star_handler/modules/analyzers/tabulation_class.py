"""Class distribution analysis for RELION.

Analyzes particle distribution across classes in RELION 3D/2D classification,
breaking down by dataset (optics groups).
"""

from pathlib import Path
from typing import Union, Dict, Tuple
import pandas as pd
import matplotlib.pyplot as plt

from ...core.io import format_input_star
from ...utils.logger import setup_logger

class ClassDistribution:
    """
    Analyze class distribution in RELION classification results.
    
    [WORKFLOW]
    1. Read classification STAR file
    2. Count particles per class per dataset
    3. Generate distribution matrix and statistics
    4. Create visualizations

    [PARAMETERS]
    star_file : Union[str, Path]
        Path to input STAR file
    group_column : str, optional
        Column defining dataset groups (default: rlnOpticsGroup)
    output_file : str, optional
        Output filename for distribution table

    [OUTPUT]
    - Distribution table (TSV)
    - Analysis report (TXT)
    - Distribution heatmap (PNG)
    - Class sizes plot (PNG)

    [EXAMPLE]
    Basic usage:
        $ star-handler star-class-distribution -f run_it150_data.star
        
    Custom group column:
        $ star-handler star-class-distribution -f particles.star -g rlnTomoName
    """
    
    def __init__(self, 
                star_file: Union[str, Path],
                group_column: str = "rlnOpticsGroup",
                output_file: str = "class_distribution.txt") -> None:
        """Initialize class distribution analyzer.
        
        [PARAMETERS]
        star_file : Union[str, Path]
            Path to input STAR file
        group_column : str, optional
            Column defining dataset groups (default: rlnOpticsGroup)
        output_file : str, optional
            Output filename for distribution table
            
        [RAISES]
        FileNotFoundError:
            If input STAR file doesn't exist
        """
        self.star_file = Path(star_file)
        if not self.star_file.exists():
            raise FileNotFoundError(f"STAR file not found: {star_file}")
            
        self.group_column = group_column
        self.output_file = output_file
        self.logger = setup_logger("class_distribution")
        
    def analyze(self) -> Tuple[pd.DataFrame, Dict]:
        """Analyze class distribution across datasets.
        
        [WORKFLOW]
        1. Read and validate STAR file
        2. Calculate distribution matrix
        3. Compute statistics
        
        [OUTPUT]
        Tuple[pd.DataFrame, Dict]:
            - Distribution matrix (datasets × classes)
            - Dictionary with additional statistics
            
        [RAISES]
        KeyError:
            If required columns are missing
        """
        self.logger.info(f"Reading STAR file: {self.star_file}")
        data = format_input_star(self.star_file)
        particles = data['particles']
        optics = data['optics']

        required_columns = ['rlnClassNumber', self.group_column]
        missing = [col for col in required_columns if col not in particles]
        if missing:
            raise KeyError(f"Missing columns in particles table: {missing}")
            
        classes = sorted(particles['rlnClassNumber'].unique())
        groups = sorted(particles[self.group_column].unique())
        
        group_name_map = dict(zip(
            optics['rlnOpticsGroup'], 
            optics['rlnOpticsGroupName']
        ))

        distribution = (
            particles
            .groupby([self.group_column, 'rlnClassNumber'])
            .size()
            .unstack(fill_value=0)
            .reindex(index=groups, columns=classes, fill_value=0)
        )
        
        distribution.index = distribution.index.map(
            lambda g: group_name_map[g]
        )
        distribution.columns = [f'class{c}' for c in distribution.columns]
        distribution.index.name = 'Dataset'

        total_particles = distribution.sum().sum()
        class_totals = distribution.sum()
        class_percentages = (class_totals / total_particles * 100).round(1)
        
        dataset_totals = distribution.sum(axis=1)
        dataset_percentages = (dataset_totals / total_particles * 100).round(1)
        
        stats = {
            'total_particles': total_particles,
            'n_classes': len(classes),
            'n_datasets': len(groups),
            'class_particles': class_totals.to_dict(),
            'class_percentages': class_percentages.to_dict(),
            'dataset_particles': dataset_totals.to_dict(),
            'dataset_percentages': dataset_percentages.to_dict(),
            'largest_class': f"class{classes[class_totals.argmax()]}",
            'largest_class_percentage': class_percentages.max()
        }
        
        return distribution, stats
        
    def save_results(self, 
                    distribution: pd.DataFrame,
                    stats: Dict,
                    output_dir: Union[str, Path] = '.') -> None:
        """Save analysis results and generate visualizations.
        
        [PARAMETERS]
        distribution : pd.DataFrame
            Class distribution matrix
        stats : Dict
            Analysis statistics
        output_dir : Union[str, Path], optional
            Output directory (default: current directory)
            
        [OUTPUT]
        - Distribution table (TSV)
        - Analysis report (TXT)
        - Distribution heatmap (PNG)
        - Class sizes plot (PNG)
        """
        output_path = Path(output_dir) if output_dir else Path('.')
        output_path.mkdir(parents=True, exist_ok=True)
        
        table_file = output_path / self.output_file
        distribution.to_csv(table_file, sep='\t', float_format="%d")
        self.logger.info(f"Saved distribution table to {table_file}")
        
        report_file = output_path / 'classification_report.txt'
        with open(report_file, 'w') as f:
            f.write("=== RELION Classification Analysis ===\n\n")
            
            f.write("Dataset Statistics:\n")
            f.write(f"- Total particles: {stats['total_particles']}\n")
            f.write(f"- Number of classes: {stats['n_classes']}\n")
            f.write(f"- Number of datasets: {stats['n_datasets']}\n")
            f.write(f"- Largest class: {stats['largest_class']} ")
            f.write(f"({stats['largest_class_percentage']:.1f}%)\n\n")
            
            f.write("Class Distribution:\n")
            for class_name, count in stats['class_particles'].items():
                percentage = stats['class_percentages'][class_name]
                f.write(f"- {class_name}: {count} particles ({percentage:.1f}%)\n")
            f.write("\n")
            
            f.write("Dataset Distribution:\n")
            for dataset, count in stats['dataset_particles'].items():
                percentage = stats['dataset_percentages'][dataset]
                f.write(f"- {dataset}: {count} particles ({percentage:.1f}%)\n")
                
        self.logger.info(f"Saved analysis report to {report_file}")
        
        plt.figure(figsize=(12, 8))
        im = plt.imshow(distribution.values, aspect='auto', cmap='YlOrRd')
        plt.colorbar(im)
        
        for i in range(len(distribution.index)):
            for j in range(len(distribution.columns)):
                text = str(distribution.values[i, j])
                plt.text(j, i, text,
                        ha='center', va='center',
                        color='black' if distribution.values[i, j] < distribution.values.max()/2 else 'white')
        
        plt.title('Particle Distribution Across Classes')
        plt.xlabel('Class')
        plt.ylabel('Dataset')
        
        plt.xticks(range(len(distribution.columns)), distribution.columns, rotation=45)
        plt.yticks(range(len(distribution.index)), distribution.index)
        
        plt.tight_layout()
        heatmap_file = output_path / 'class_distribution_heatmap.png'
        plt.savefig(heatmap_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        plt.figure(figsize=(10, 6))
        class_percentages = pd.Series(stats['class_percentages'])
        class_percentages.plot(kind='bar')
        plt.title('Class Size Distribution')
        plt.xlabel('Class')
        plt.ylabel('Percentage of Particles')
        plt.xticks(rotation=45)
        plt.tight_layout()
        barplot_file = output_path / 'class_sizes.png'
        plt.savefig(barplot_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Generated visualizations in {output_path}")
