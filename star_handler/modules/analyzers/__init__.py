"""
STAR file analysis modules.

Provides a collection of analyzers for different types of particle analysis:
- Radial distribution [g(r)]
- Particle clustering
- Orientation analysis
- Ribosome neighbor analysis
"""

from .base import BaseAnalyzer
from .radial import RadialAnalyzer
from .cluster import ClusterAnalyzer
from .orientation import OrientationAnalyzer


__all__ = [
    'BaseAnalyzer',
    'AnalysisError',
    'RadialAnalyzer',
    'ClusterAnalyzer',
    'OrientationAnalyzer',
]

# Example usage:
"""
from . import RadialAnalyzer

analyzer = RadialAnalyzer('particles.star', bin_size=50)
results = analyzer.process()
"""
