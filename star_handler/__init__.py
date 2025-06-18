"""
STAR Handler - A comprehensive toolkit for analyzing RELION STAR files
"""

__version__ = "2.0.0"

from star_handler.analyzers.cluster import ClusterAnalyzer
from star_handler.analyzers.orientation import OrientationAnalyzer
from star_handler.analyzers.orientation_comparer import OrientationComparer
from star_handler.analyzers.radial import RadialAnalyzer
from star_handler.analyzers.ribosome_neighbor import RibosomeNeighborAnalyzer
from star_handler.analyzers.ribosome_spatial import RibosomeSpatialAnalyzer
from star_handler.analyzers.tabulation_class import ClassDistribution

from star_handler.core.star_handler import classify_star, split_star_by_threshold

from star_handler.processors.conditional_modify import ConditionalModifyProcessor
from star_handler.processors.filter_by_ref import FilterByRefProcessor
from star_handler.processors.relion2cbox import Relion2CboxProcessor
from star_handler.processors.template_match import TemplateMatch3DProcessor
from star_handler.processors.warp2relion import Warp2RelionProcessor


__all__ = [
    "ClassDistribution",
    "ClusterAnalyzer",
    "OrientationAnalyzer",
    "OrientationComparer",
    "RadialAnalyzer",
    "RibosomeNeighborAnalyzer",
    "RibosomeSpatialAnalyzer",
    "classify_star",
    "split_star_by_threshold",
    "ConditionalModifyProcessor",
    "FilterByRefProcessor",
    "Relion2CboxProcessor",
    "TemplateMatch3DProcessor",
    "Warp2RelionProcessor",
]
