"""
Core functionality for STAR file handling and mathematical operations.
"""

from star_handler.core.star_handler import (
    format_input_star,
    format_output_star,
    find_tomogram_name,
    scale_coord,
    apply_shift,
    threshold_star,
    split_by_tomogram,
    add_particle_names,
    parallel_process_tomograms,
    merge_for_match,
    m_to_rln
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
    # Star handling functions
    "format_input_star",
    "format_output_star",
    "find_tomogram_name",
    "scale_coord",
    "apply_shift",
    "threshold_star",
    "split_by_tomogram",
    "select_correspond_particle",
    "add_particle_names",
    "parallel_process_tomograms",
    "merge_for_match",
    "m_to_rln",
    
    # Math operations
    "euler_to_vector",
    "calculate_orientation_angle",
    "dfs",
    "UnionFind",
    "build_adjacency_matrix",
    "find_particle_clusters"
]
