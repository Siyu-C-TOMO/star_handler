"""
Core functionality for STAR file handling and mathematical operations.
"""

from .io import (
    format_input_star,
    format_output_star,
)
from .selection import (
    classify_star,
    split_star_by_threshold,
    threshold_star,
)
from .transform import (
    apply_shift,
    scale_coord,
    add_particle_names,
    merge_for_match,
    m_to_rln,
)
from .parallel import (
    parallel_process_tomograms,
)

from star_handler.core.matrix_math import (
    euler_to_vector,
    calculate_orientation_angle,
    dfs,
    UnionFind,
    build_adjacency_matrix,
    find_particle_clusters
)

__all__ = [
    # I/O
    "format_input_star",
    "format_output_star",

    # Selection
    "classify_star",
    "split_star_by_threshold",
    "threshold_star",

    # Transform
    "apply_shift",
    "scale_coord",
    "add_particle_names",
    "merge_for_match",
    "m_to_rln",

    # Parallel
    "parallel_process_tomograms",
    
    # Math operations
    "euler_to_vector",
    "calculate_orientation_angle",
    "dfs",
    "UnionFind",
    "build_adjacency_matrix",
    "find_particle_clusters"
]
