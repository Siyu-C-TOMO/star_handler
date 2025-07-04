import argparse
from pathlib import Path

# --- Templates ---

ANALYZER_TEMPLATE = """
from .base import BaseAnalyzer, AnalysisError

class {class_name}(BaseAnalyzer):
    \"\"\"
    A brief, one-line summary of the component.

    A more detailed description of the component's purpose and functionality.

    [Workflow]
    1. Step one of the process.
    2. Step two of the process.
    3. ...

    [Parameters]
    param_one : str
        Description of the first parameter.
    
    [OUTPUT]
    dict
        Description of the return value.

    [RAISES]
    AnalysisError
        If the analysis fails.

    [EXAMPLE]
    >>> analyzer = {class_name}()
    >>> analyzer.process()
    \"\"\"
    ANALYSIS_TYPE = "{analyzer_name}"
    
    def __init__(self, star_file: str, **config_params):
        super().__init__(star_file, **config_params)
        # Your initialization logic here

    def _analyze(self, data, coords, dist_matrix):
        # Your core analysis logic for a single tomogram here
        pass

    def _combine_results(self, results):
        # Your logic to combine results from all tomograms here
        pass

    def _generate_report(self, results):
        # Your logic to generate a final report here
        pass
        
    def _save_tomogram_results(self, tomogram, results):
        # Your logic to save results for a single tomogram here
        pass
"""

PROCESSOR_TEMPLATE = """
from .base import BaseProcessor
from ...utils.errors import ProcessingError

class {class_name}(BaseProcessor):
    \"\"\"
    A brief, one-line summary of the component.

    A more detailed description of the component's purpose and functionality.

    [Workflow]
    1. Step one of the process.
    2. Step two of the process.
    3. ...

    [Parameters]
    param_one : str
        Description of the first parameter.
    
    [OUTPUT]
    None
        This processor modifies files in place or creates new ones.

    [RAISES]
    ProcessingError
        If the processing fails.

    [EXAMPLE]
    >>> processor = {class_name}()
    >>> processor.process()
    \"\"\"
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Your initialization logic here

    def process(self):
        # Your core processing logic here
        pass
"""

COMPARER_TEMPLATE = """
from .base import BaseComparer, AnalysisError

class {class_name}(BaseComparer):
    \"\"\"
    A brief, one-line summary of the component.

    A more detailed description of the component's purpose and functionality.

    [Workflow]
    1. Step one of the process.
    2. Step two of the process.
    3. ...

    [Parameters]
    param_one : str
        Description of the first parameter.
    
    [OUTPUT]
    dict
        Description of the return value.

    [RAISES]
    AnalysisError
        If the comparison fails.

    [EXAMPLE]
    >>> comparer = {class_name}()
    >>> comparer.compare()
    \"\"\"
    def __init__(self, file1: str, file2: str, output_dir: str = "{default_output_dir}"):
        super().__init__(file1=file1, file2=file2, output_dir=output_dir)
        # Your initialization logic here

    def compare(self):
        # Your core comparison logic here
        pass
"""

COMMAND_TEMPLATE = """
import sys
import click

from star_handler.modules.{module_type}.{module_name} import {class_name}
from star_handler.utils.logger import setup_logger
from star_handler.utils.doc_parser import parse_docstring

logger = setup_logger(__name__)

HELP, EPILOG = parse_docstring({class_name}.__doc__)

@click.command(
    name='star-{command_name}',
    help=HELP,
    epilog=EPILOG
)
# Add your @click.option decorators here
@click.option(
    "-o", "--output-dir",
    default="{default_output_dir}",
    show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Output directory for results."
)
def main(**kwargs):
    \"\"\"
    Command-line interface for running the {command_name} command.
    \"\"\"
    try:
        logger.info("Starting {command_name}...")
        # Pass kwargs to the class constructor
        instance = {class_name}(**kwargs)
        
        # Dynamically call the main method of the class
        if hasattr(instance, 'run'):
            instance.run()
        elif hasattr(instance, 'process'):
            instance.process()
        elif hasattr(instance, 'compare'):
            instance.compare()
        else:
            raise NotImplementedError(f"The class {class_name} does not have a standard run method.")

        logger.info("Command complete.")
        print(f"{class_name} complete. Results saved in '{kwargs.get('output_dir')}'")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
"""

def to_camel_case(snake_str):
    return "".join(x.capitalize() for x in snake_str.split('_'))

def main():
    parser = argparse.ArgumentParser(
        description="Scaffolding tool for creating new star_handler commands."
    )
    parser.add_argument(
        "name",
        type=str,
        help="Base name for the new command in snake_case (e.g., 'proximity_comparison')."
    )
    parser.add_argument(
        "type",
        choices=['analyzer', 'comparer', 'processor'],
        help="Type of the command."
    )
    args = parser.parse_args()

    base_path = Path(__file__).parent.parent
    modules_path = base_path / "star_handler" / "modules"
    commands_path = base_path / "star_handler" / "cli" / "commands"

    base_name = args.name.replace('-', '_')
    module_name = base_name
    camel_name = to_camel_case(base_name)
    command_name = base_name.replace('_', '-')
    
    if args.type == 'analyzer':
        class_name = f"{camel_name}Analyzer"
        template = ANALYZER_TEMPLATE
        module_path = modules_path / "analyzers"
        module_type = "analyzers"
    elif args.type == 'comparer':
        class_name = f"{camel_name}Comparer"
        template = COMPARER_TEMPLATE
        module_path = modules_path / "comparers"
        module_type = "comparers"
    else:  # processor
        class_name = f"{camel_name}Processor"
        template = PROCESSOR_TEMPLATE
        module_path = modules_path / "processors"
        module_type = "processors"

    default_output = base_name

    # Ensure the target directory exists
    module_path.mkdir(parents=True, exist_ok=True)

    module_content = template.format(
        class_name=class_name,
        analyzer_name=base_name, # Keep for compatibility with analyzer template
        default_output_dir=default_output
    )
    module_file = module_path / f"{module_name}.py"
    if module_file.exists():
        print(f"Error: File already exists at {module_file}")
    else:
        module_file.write_text(module_content)
        print(f"Successfully created module: {module_file}")

    # Ensure the target directory exists
    commands_path.mkdir(parents=True, exist_ok=True)

    command_content = COMMAND_TEMPLATE.format(
        command_name=command_name,
        module_name=module_name,
        class_name=class_name,
        module_type=module_type,
        default_output_dir=default_output
    )
    command_file = commands_path / f"{module_name}.py"
    if command_file.exists():
        print(f"Error: File already exists at {command_file}")
    else:
        command_file.write_text(command_content)
        print(f"Successfully created command: {command_file}")

if __name__ == "__main__":
    main()
