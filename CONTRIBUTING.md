# Contributing to star_handler_v2

Thank you for your interest in contributing! This document outlines the conventions and best practices to follow when adding new features to this project.

## Core Technologies

- **Command-Line Interface (CLI)**: [Click](https://click.palletsprojects.com/)
- **Core Data Structure**: [pandas.DataFrame](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html)
- **Numerical Operations**: [NumPy](https://numpy.org/) & [SciPy](https://scipy.org/)

## Code Style & Conventions

### Docstrings

All major classes and functions should have a docstring that follows the project's specific format. This format is parsed by `utils/doc_parser.py` to automatically generate help messages for the CLI.

**Template:**
```python
"""
A brief, one-line summary of the component.

A more detailed description of the component's purpose and functionality.

[Workflow]
1. Step one of the process.
2. Step two of the process.
3. ...

[Parameters]
param_one : str
    Description of the first parameter.
param_two : int, optional
    Description of the second parameter. Defaults to 0.

[OUTPUT]
str
    Description of the return value.

[RAISES]
ValueError
    Description of when this error is raised.

[EXAMPLE]
>>> component = MyComponent()
>>> component.run()
"""
```

### Logging

Use the `setup_logger` utility from `utils/logger.py` to create a logger instance for your module. This ensures consistent log formatting.

```python
from star_handler.utils.logger import setup_logger
logger = setup_logger(__name__)
```

### Error Handling

Use the custom exception classes defined in `analyzers/base.py` (e.g., `AnalysisError`) or `core/matrix_math.py` (e.g., `MathError`) where appropriate to provide more specific error feedback.

## Adding a New Command

To streamline development and ensure consistency, use the provided scaffolding script to generate the boilerplate for a new command.

### Usage

1.  Navigate to the `scripts` directory:
    ```bash
    cd star_handler_v2/scripts
    ```

2.  Run the `create_new_command.py` script with the desired `name` and `type`:
    ```bash
    # For a command that compares two STAR files
    python create_new_command.py my_comparison_feature comparer

    # For a command that analyzes a single STAR file
    python create_new_command.py my_analysis_feature analyzer
    ```

### What It Does

The script will automatically create two files based on a consistent naming convention:

-   **Analyzer/Comparer File**: `star_handler/analyzers/my_comparison_feature.py`
    - Contains a template class (`MyComparisonFeatureComparer`) that inherits from the correct base class.
    - Includes a pre-formatted docstring and placeholder methods.

-   **Command File**: `star_handler/cli/commands/my_comparison_feature.py`
    - Contains a pre-configured `click` command (`star-my-comparison-feature`).
    - Automatically linked to the new analyzer/comparer class.

Your task is then reduced to filling in the core logic in the generated `.../analyzers/` file and adding any specific command-line options to the `.../cli/commands/` file.

### Command Discovery

**No further action is needed.** The project's main entry point (`star_handler/__main__.py`) uses a dynamic loading system. It automatically discovers and registers your new command once the files are created.
