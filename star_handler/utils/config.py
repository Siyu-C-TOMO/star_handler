"""Configuration for particle analysis parameters.

Provides simple configuration classes for:
- Radial distribution analysis
- Cluster analysis 
- Orientation analysis
- Ribosome neighbor analysis
- Class distribution analysis
- RELION to CryoLO conversion
- Reference-based filtering
"""

from dataclasses import dataclass

@dataclass
class ClassDistributionConfig:
    """Configuration for class distribution analysis.
    
    [ATTRIBUTES]
    group_column : str
        Column defining dataset groups
    output_file : str
        Output filename for distribution table
    """
    group_column: str = "rlnOpticsGroup"
    output_file: str = "class_distribution.txt"

@dataclass
class Relion2CboxConfig:
    """Configuration for RELION to CryoLO conversion.
    
    [ATTRIBUTES]
    bin_factor : int
        Scale factor for unbinning coordinates
    """
    bin_factor: int = 1

@dataclass
class FilterByRefConfig:
    """Configuration for reference-based filtering."""
    pass

@dataclass
class RadialConfig:
    """Configuration for radial distribution analysis.
    
    [ATTRIBUTES]
    bin_size : float
        Size of distance bins (Å)
    min_distance : float  
        Minimum distance to consider (Å)
    max_distance : float
        Maximum distance to consider (Å)
    """
    bin_size: float = 50.0
    min_distance: float = 175.0  # Half ribosome diameter
    max_distance: float = 7000.0

@dataclass 
class ClusterConfig:
    """Configuration for cluster analysis.
    
    [ATTRIBUTES]
    threshold : float
        Distance threshold for clustering (Å)
    min_cluster_size : int 
        Minimum number of particles per cluster
    """
    threshold: float = 380.0
    min_cluster_size: int = 1

@dataclass
class OrientationConfig:
    """Configuration for orientation analysis.
    
    [ATTRIBUTES]
    max_angle : float
        Maximum angle to consider (degrees)
    bin_width : float  
        Width of angle bins (degrees)
    """
    max_angle: float = 180.0
    bin_width: float = 3.0

@dataclass
class RibosomeNeighborConfig:
    """Configuration for ribosome neighbor analysis.
    
    [ATTRIBUTES]
    search_radius : float
        Maximum distance for considering neighbors (Å)
    bin_size : float
        Size of bins for distance histogram (Å)
    """
    search_radius: float = 500.0
    bin_size: float = 10.0
