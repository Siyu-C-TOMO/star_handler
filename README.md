# STAR Handler v2

A comprehensive toolkit for analyzing and processing RELION STAR files, with a focus on particle distribution, spatial analysis, and format conversion.

## Features

- **Particle Classification**: Organize particles by metadata tags with flexible matching options.
- **Radial Distribution Analysis**: Calculate g(r) to analyze particle spatial distributions.
- **Cluster Analysis**: Identify and analyze particle clusters based on spatial proximity.
- **Orientation Analysis**: Analyze particle orientations and their relationships.
- **Class Distribution Analysis**: Analyze particle distribution across classification results.
- **Orientation Comparison**: Compare particle orientations between two corresponding STAR files.
- **Ribosome Neighbor Analysis**: Analyze spatial relationships between neighboring ribosomes, including entry/exit site distances.
- **Comprehensive Spatial Analysis**: Perform combined radial, cluster, and orientation analyses in one pass.
- **Conditional Modification**: Modify columns in a STAR file based on specific conditions.
- **Reference-based Filtering**: Filter a STAR file based on the particles present in a reference STAR file.
- **Threshold-based Splitting**: Split a STAR file into multiple files based on value thresholds.
- **Data Preparation**: Prepare STAR files for Relion 3 and Relion 5.
- **M refinement**: Run M refinement from multiple datasets.
- **Format Conversion**: Convert STAR files from Warp/MotionCor2 format to RELION format, and generate CryoLO cbox files from RELION coordinates.

## Installation

### From Source
```bash
git clone https://github.com/Siyu-C-TOMO/star_handler.git
cd star_handler/
pip install -r requirements.txt
pip install -e .
```

## Configuration

### Slack Notifications
The package includes built-in Slack notifications for long-running operations. To enable:

1. Create a Slack App in your workspace
2. Add the Bot Token to your environment:
```bash
export SLACK_BOT_TOKEN="xoxb-your-token"
```
3. Use the notification decorator in your code:
```python
from star_handler.utils.logger import log_execution

@log_execution(notify=True)
def your_function():
    pass
```

## Quick Start

### Command Line Interface

1.  **Analyze particle clusters**:
    ```bash
    star-handler analyze-cluster -f particles.star -t 380
    ```
2.  **Analyze class distribution**:
    ```bash
    star-handler analyze-class-distribution -f run_it150_data.star
    ```
3.  **Analyze particle orientations**:
    ```bash
    star-handler analyze-orientation -f particles.star
    ```
4.  **Analyze radial distribution**:
    ```bash
    star-handler analyze-radial -f particles.star -b 50 -m 8000
    ```
5.  **Run comprehensive ribosome spatial analysis**:
    ```bash
    star-handler analyze-ribo-spatial -f particles.star
    ```
6.  **Compare particle orientations**:
    ```bash
    star-handler compare-orientation --env-star env.star --mem-star mem.star
    ```
7.  **Compare proximity/neighbor rate**:
    ```bash
    star-handler compare-neighbor-rate --star-a set_a.star --star-b set_b.star --threshold 50.0
    ```
8.  **Compare ribosome polysome structure**:
    ```bash
    star-handler compare-ribo-polysome -f r.star -en entry.star -ex exit.star -r 600
    ```
9.  **Prepare STAR file for Relion 3**:
    ```bash
    star-handler process-relion3-prep -f your_file.star
    ```
10. **Prepare STAR file for Relion 5**:
    ```bash
    star-handler process-relion5-prep -f your_file.star
    ```
11. **Run M refinement from multiple datasets**:
    ```bash
    star-handler process-m-combine -p "pattern_*.star" -o combined.star
    ```
12. **Classify particles by tomogram**:
    ```bash
    star-handler process-classify-by-tomo -f particles.star
    ```
13. **Filter a STAR file by matching another**:
    ```bash
    star-handler process-filter-by-match -f full.star -r ref.star
    ```
14. **Modify a STAR file based on a condition**:
    ```bash
    star-handler process-modify-by-match -f p.star -c 1 -s "mic/"
    ```
15. **Convert RELION coordinates to cryoLO format**:
    ```bash
    star-handler process-relion2cryolo -f run_data.star -b 4
    ```
16. **Split a STAR file by a value threshold**:
    ```bash
    star-handler process-split-by-thres -f p.star -t rlnAngleTilt -th 45.0
    ```
17. **Convert a Warp STAR file to RELION format**:
    ```bash
    star-handler process-warp2relion -f warp_particles.star
    ```

### Python API

```python
from star_handler.modules.analyzers import (
    RadialAnalyzer, ClusterAnalyzer, OrientationAnalyzer, ClassDistribution,
    RibosomeSpatialAnalyzer
)
from star_handler.modules.comparers import (
    OrientationComparer, RibosomeNeighborComparer, ProximityComparer
)
from star_handler.modules.processors import (
    ConditionalModifyProcessor, FilterByRefProcessor, Relion2CboxProcessor,
    Warp2RelionProcessor, Relion3PrepProcessor, Relion5PrepProcessor, MCombineProcessor
)
from star_handler.core.selection import classify_star, split_star_by_threshold

# Classify particles
classify_star("particles.star", tag="rlnClassNumber")

# Split particles by threshold
split_star_by_threshold('data.star', 'rlnAngleTilt', 45.0)

# Radial analysis
radial = RadialAnalyzer("particles.star", bin_size=50)
radial.process()

# Cluster analysis
cluster = ClusterAnalyzer("particles.star", threshold=380)
cluster.process()

# Orientation analysis
orientation = OrientationAnalyzer("particles.star")
orientation.process()

# Class distribution analysis
distribution = ClassDistribution("run_it150_data.star")
distribution.analyze()

# Compare Orientations
comparer = OrientationComparer("env.star", "mem.star")
comparer.compare()

# Ribosome Neighbor Analysis
neighbor_analyzer = RibosomeNeighborComparer("r.star", "entry.star", "exit.star")
neighbor_analyzer.process()

# Comprehensive Spatial Analysis
spatial_analyzer = RibosomeSpatialAnalyzer("particles.star")
spatial_analyzer.run_analysis()

# Conditional Modify
modifier = ConditionalModifyProcessor("p.star", "1", "mic/")
modifier.process()

# Filter by Reference
filtrator = FilterByRefProcessor("full.star", "ref.star")
filtrator.process()

# Warp to Relion
warp_converter = Warp2RelionProcessor("warp.star")
warp_converter.process()

# Relion to CBOX
cbox_converter = Relion2CboxProcessor("relion.star", bin_factor=4)
cbox_converter.process()

# Relion 3 Prep
relion3_prep = Relion3PrepProcessor("your_file.star")
relion3_prep.process()

# Relion 5 Prep
relion5_prep = Relion5PrepProcessor("your_file.star")
relion5_prep.process()

# M Combine
m_combiner = MCombineProcessor(pattern="pattern_*.star", output_file="combined.star")
m_combiner.process()
```

## Requirements

- Python >= 3.8
- NumPy
- Pandas
- Matplotlib
- SciPy
- Starfile
- Click

## Development

1.  Clone the repository.
2.  Install development dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run tests:
    ```bash
    pytest
    ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
