"""
STAR Handler - A comprehensive toolkit for analyzing RELION STAR files
"""

__version__ = "2.0.0"

from .modules.analyzers.cluster import ClusterAnalyzer
from .modules.analyzers.orientation import OrientationAnalyzer
from .modules.analyzers.radial import RadialAnalyzer
from .modules.analyzers.ribosome_spatial import RibosomeSpatialAnalyzer
from .modules.analyzers.tabulation_class import ClassDistribution
from .modules.comparers.orientation_comparer import OrientationComparer
from .modules.comparers.ribosome_neighbor import RibosomeNeighborComparer
from .modules.comparers.proximity_comparer import ProximityComparer

from .core.selection import classify_star, split_star_by_threshold

from .modules.processors.conditional_modify import ConditionalModifyProcessor
from .modules.processors.filter_by_ref import FilterByRefProcessor
from .modules.processors.relion2cbox import Relion2CboxProcessor
from .modules.processors.template_match import TemplateMatch3DProcessor
from .modules.processors.warp2relion import Warp2RelionProcessor
from .modules.processors.add_helical import AddHelByRefProcessor



__all__ = [
    "ClassDistribution",
    "ClusterAnalyzer",
    "OrientationAnalyzer",
    "RadialAnalyzer",
    "RibosomeSpatialAnalyzer",
    "OrientationComparer",
    "RibosomeNeighborComparer",
    "ProximityComparer",
    "classify_star",
    "split_star_by_threshold",
    "ConditionalModifyProcessor",
    "FilterByRefProcessor",
    "Relion2CboxProcessor",
    "TemplateMatch3DProcessor",
    "Warp2RelionProcessor",
    "AddHelByRefProcessor",
]
