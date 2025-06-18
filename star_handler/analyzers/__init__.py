"""
STAR file analysis modules.

Provides a collection of analyzers for different types of particle analysis:
- Radial distribution [g(r)]
- Particle clustering
- Orientation analysis
- Ribosome neighbor analysis
"""

from star_handler.analyzers.base import BaseAnalyzer, AnalysisError
from star_handler.analyzers.radial import RadialAnalyzer
from star_handler.analyzers.cluster import ClusterAnalyzer
from star_handler.analyzers.orientation import OrientationAnalyzer
from star_handler.analyzers.ribosome_neighbor import RibosomeNeighborAnalyzer
from star_handler.analyzers.orientation_comparer import OrientationComparer

__all__ = [
    'BaseAnalyzer',
    'AnalysisError',
    'RadialAnalyzer',
    'ClusterAnalyzer',
    'OrientationAnalyzer',
    'RibosomeNeighborAnalyzer',
    'OrientationComparer'
]

# Example usage:
"""
from star_handler.analyzers import RadialAnalyzer

analyzer = RadialAnalyzer('particles.star', bin_size=50)
results = analyzer.process()
"""
