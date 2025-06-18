"""
Mathematical operations for particle analysis.

This module provides mathematical utilities for:
- Coordinate transformations
- Orientation calculations
- Clustering operations
- Radial distribution analysis
"""

import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.spatial import KDTree
from typing import List, Tuple, Dict

class MathError(Exception):
    """Base exception for mathematical operations."""
    pass

class TransformationError(MathError):
    """Raised when coordinate transformations fail."""
    pass

class ClusteringError(MathError):
    """Raised when clustering operations fail."""
    pass

class RadialAnalysisError(MathError):
    """Raised when radial analysis calculations fail."""
    pass

def euler_to_vector(rot: float, tilt: float, psi: float) -> np.ndarray:
    """Convert Euler angles to direction vector.
    
    [WORKFLOW]
    1. Create rotation from Euler angles
    2. Apply to unit vector
    3. Flip x-coordinate for RELION convention
    
    [PARAMETERS]
    rot : float
        Rotation angle (degrees)
    tilt : float
        Tilt angle (degrees)
    psi : float
        Psi angle (degrees)
        
    [OUTPUT]
    np.ndarray
        3D direction vector
        
    [RAISES]
    TransformationError
        If conversion fails
        
    [EXAMPLE]
    >>> v = euler_to_vector(0, 30, 0)
    """
    try:
        rotation = R.from_euler('zyz', [rot, tilt, psi], degrees=True)
        v = np.array([0, 0, 1])
        v_rotated = rotation.apply(v)
        v_rotated[0] = -v_rotated[0]  # RELION convention
        return v_rotated
    except Exception as e:
        raise TransformationError(f"Euler angle conversion failed: {str(e)}")

def calculate_orientation_angle(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate angle between two vectors.
    
    [WORKFLOW]
    1. Normalize vectors
    2. Calculate dot product
    3. Convert to angle in degrees
    
    [PARAMETERS]
    vec1, vec2 : np.ndarray
        3D vectors to compare
        
    [OUTPUT]
    float
        Angle in degrees
        
    [RAISES]
    MathError
        If calculation fails
        
    [EXAMPLE]
    >>> angle = calculate_orientation_angle([1,0,0], [0,1,0])
    """
    try:
        vec1_norm = vec1 / np.linalg.norm(vec1)
        vec2_norm = vec2 / np.linalg.norm(vec2)
        
        dot_product = np.dot(vec1_norm, vec2_norm)
        dot_product = np.clip(dot_product, -1.0, 1.0)
        
        return np.degrees(np.arccos(dot_product))
    except Exception as e:
        raise MathError(f"Angle calculation failed: {str(e)}")

def shell_normalize(hist: np.ndarray,
                   bins: np.ndarray,
                   box_volume: float,
                   n_particles: int) -> np.ndarray:
    """Normalize histogram by shell volumes and number density.
    
    [WORKFLOW]
    1. Calculate shell volumes
    2. Calculate number density
    3. Normalize counts
    
    [PARAMETERS]
    hist : np.ndarray
        Distance histogram
    bins : np.ndarray
        Bin edges for histogram
    box_volume : float
        Volume of analysis box
    n_particles : int
        Number of particles
        
    [OUTPUT]
    np.ndarray
        Normalized histogram
    """
    try:
        shell_volumes = 4/3 * np.pi * (bins[1:]**3 - bins[:-1]**3)
        number_density = n_particles / box_volume
        norm = number_density * shell_volumes
        
        return np.divide(
            hist / n_particles,
            norm,
            out=np.zeros_like(hist, dtype=float),
            where=norm > 0
        )
    except Exception as e:
        raise RadialAnalysisError(f"Shell normalization failed: {str(e)}")

def safe_histogram(distances: np.ndarray,
                  bins: np.ndarray) -> np.ndarray:
    """Create histogram with validation.
    
    [WORKFLOW]
    1. Validate inputs
    2. Create histogram
    3. Handle edge cases
    
    [PARAMETERS]
    distances : np.ndarray
        Distance array
    bins : np.ndarray
        Bin edges
        
    [OUTPUT]
    np.ndarray
        Distance histogram
    """
    try:
        if len(distances) == 0:
            return np.zeros(len(bins) - 1)
            
        hist, _ = np.histogram(distances, bins=bins)
        return hist
    except Exception as e:
        raise RadialAnalysisError(f"Histogram creation failed: {str(e)}")

def gr(distances: np.ndarray,
       bins: np.ndarray,
       box_volume: float,
       n_particles: int) -> np.ndarray:
    """Compute radial distribution function g(r).
    
    [WORKFLOW]
    1. Create distance histogram
    2. Normalize by shell volumes and density
    
    [PARAMETERS]
    distances : np.ndarray
        Array of pairwise distances
    bins : np.ndarray
        Bin edges for histogram
    box_volume : float
        Volume of analysis box
    n_particles : int
        Number of particles
        
    [OUTPUT]
    np.ndarray
        g(r) values
    """
    try:
        hist = safe_histogram(distances, bins)
        return shell_normalize(hist, bins, box_volume, n_particles)
    except Exception as e:
        raise RadialAnalysisError(f"g(r) calculation failed: {str(e)}")

def local_density(distances: np.ndarray,
                 bins: np.ndarray,
                 box_volume: float,
                 n_particles: int) -> np.ndarray:
    """Compute local density distribution.
    
    [WORKFLOW]
    1. Create distance histogram
    2. Normalize by expected number of pairs
    
    [PARAMETERS]
    distances : np.ndarray
        Array of pairwise distances
    bins : np.ndarray
        Bin edges for histogram
    box_volume : float
        Volume of analysis box
    n_particles : int
        Number of particles
        
    [OUTPUT]
    np.ndarray
        Local density values
    """
    try:
        hist = safe_histogram(distances, bins)
        shell_volumes = 4/3 * np.pi * (bins[1:]**3 - bins[:-1]**3)
        expected_pairs = (n_particles * (n_particles - 1) / 2) * (shell_volumes / box_volume)
        
        return np.divide(
            hist,
            expected_pairs,
            out=np.zeros_like(hist, dtype=float),
            where=expected_pairs != 0
        )
    except Exception as e:
        raise RadialAnalysisError(f"Local density calculation failed: {str(e)}")

def distance_weighted(distances: np.ndarray,
                     bins: np.ndarray) -> np.ndarray:
    """Compute r² weighted distribution.
    
    [WORKFLOW]
    1. Create distance histogram
    2. Normalize by r²
    
    [PARAMETERS]
    distances : np.ndarray
        Array of pairwise distances
    bins : np.ndarray
        Bin edges for histogram
        
    [OUTPUT]
    np.ndarray
        Distance-weighted values
    """
    try:
        hist = safe_histogram(distances, bins)
        bin_centers = 0.5 * (bins[1:] + bins[:-1])
        r_squared = bin_centers**2
        
        return np.divide(
            hist,
            r_squared,
            out=np.zeros_like(hist, dtype=float),
            where=r_squared != 0
        )
    except Exception as e:
        raise RadialAnalysisError(f"Distance weighting failed: {str(e)}")

def dfs(particle: int,
        visited: set,
        adjacency_matrix: np.ndarray,
        cluster: List[int]) -> None:
    """Depth-first search for connected particles.
    
    [WORKFLOW]
    1. Mark current particle as visited
    2. Add to current cluster
    3. Recursively visit neighbors
    
    [PARAMETERS]
    particle : int
        Current particle index
    visited : set
        Set of visited particles
    adjacency_matrix : np.ndarray
        Boolean matrix of particle connections
    cluster : List[int]
        Current cluster being built
        
    [RAISES]
    ClusteringError
        If DFS fails
        
    [EXAMPLE]
    >>> dfs(0, set(), adjacency, [])
    """
    try:
        visited.add(particle)
        cluster.append(particle)
        
        neighbors = np.where(adjacency_matrix[particle])[0]
        for neighbor in neighbors:
            if neighbor not in visited:
                dfs(neighbor, visited, adjacency_matrix, cluster)
    except Exception as e:
        raise ClusteringError(f"DFS traversal failed: {str(e)}")

class UnionFind:
    """Union-Find data structure for efficient clustering.
    
    Supports:
    - Path compression
    - Union by rank
    - Set size tracking
    """
    
    def __init__(self, n: int):
        """Initialize with n elements.
        
        [PARAMETERS]
        n : int
            Number of elements
        """
        self.parent = list(range(n))
        self.rank = [0] * n
        self.size = [1] * n
        
    def find(self, x: int) -> int:
        """Find set representative with path compression.
        
        [PARAMETERS]
        x : int
            Element to find
            
        [OUTPUT]
        int
            Representative element
            
        [RAISES]
        ClusteringError
            If find operation fails
        """
        try:
            if self.parent[x] != x:
                self.parent[x] = self.find(self.parent[x])
            return self.parent[x]
        except Exception as e:
            raise ClusteringError(f"Find operation failed: {str(e)}")
    
    def union(self, x: int, y: int) -> None:
        """Union sets by rank.
        
        [PARAMETERS]
        x, y : int
            Elements to union
            
        [RAISES]
        ClusteringError
            If union operation fails
        """
        try:
            px, py = self.find(x), self.find(y)
            if px == py:
                return
                
            if self.rank[px] < self.rank[py]:
                px, py = py, px
                
            self.parent[py] = px
            self.size[px] += self.size[py]
            
            if self.rank[px] == self.rank[py]:
                self.rank[px] += 1
        except Exception as e:
            raise ClusteringError(f"Union operation failed: {str(e)}")

def build_adjacency_matrix(coords: np.ndarray,
                         threshold: float) -> np.ndarray:
    """Build adjacency matrix using KDTree.
    
    [WORKFLOW]
    1. Validate input coordinates
    2. Build KDTree
    3. Find pairs within threshold
    
    [PARAMETERS]
    coords : np.ndarray
        Particle coordinates (N, 3)
    threshold : float
        Distance threshold
        
    [OUTPUT]
    np.ndarray
        Boolean adjacency matrix
        
    [RAISES]
    ClusteringError
        If matrix construction fails
        
    [EXAMPLE]
    >>> adj_mat = build_adjacency_matrix(coords, 100.0)
    """
    try:
        if coords.ndim != 2 or coords.shape[1] != 3:
            raise ValueError("Coordinates must be Nx3 array")
            
        n_particles = coords.shape[0]
        adjacency = np.zeros((n_particles, n_particles), dtype=bool)
        
        tree = KDTree(coords)
        pairs = tree.query_pairs(threshold, output_type='ndarray')
        
        if len(pairs) > 0:
            adjacency[pairs[:, 0], pairs[:, 1]] = True
            adjacency[pairs[:, 1], pairs[:, 0]] = True
            
        return adjacency
    except Exception as e:
        raise ClusteringError(f"Adjacency matrix construction failed: {str(e)}")

def find_particle_clusters(adjacency_matrix: np.ndarray
                         ) -> Tuple[List[List[int]], Dict[int, int]]:
    """Find particle clusters using Union-Find.
    
    [WORKFLOW]
    1. Initialize Union-Find structure
    2. Process particle pairs
    3. Collect clusters
    4. Calculate size distribution
    
    [PARAMETERS]
    adjacency_matrix : np.ndarray
        Boolean adjacency matrix
        
    [OUTPUT]
    Tuple[List[List[int]], Dict[int, int]]:
        - List of clusters (particle indices)
        - Size distribution dictionary
        
    [RAISES]
    ClusteringError
        If clustering fails
        
    [EXAMPLE]
    >>> clusters, sizes = find_particle_clusters(adj_mat)
    """
    try:
        n_particles = adjacency_matrix.shape[0]
        uf = UnionFind(n_particles)
        
        # Merge connected particles
        pairs = np.where(np.triu(adjacency_matrix, k=1))
        for i, j in zip(*pairs):
            uf.union(i, j)
            
        # Collect clusters
        cluster_dict = {}
        for i in range(n_particles):
            root = uf.find(i)
            if root not in cluster_dict:
                cluster_dict[root] = []
            cluster_dict[root].append(i)
            
        clusters = list(cluster_dict.values())
        
        size_distribution = {}
        for cluster in clusters:
            size = len(cluster)
            size_distribution[size] = size_distribution.get(size, 0) + 1
            
        return clusters, size_distribution
    except Exception as e:
        raise ClusteringError(f"Cluster identification failed: {str(e)}")
