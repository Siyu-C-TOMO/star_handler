"""
Core I/O functionality for handling STAR files.
"""
import logging
import subprocess
import os
from pathlib import Path
from typing import Dict, Union, List, Optional
import pandas as pd
import starfile

from ..utils.errors import StarFileError, FormatError

def format_input_star(file_name: Union[str, Path]) -> Dict[str, pd.DataFrame]:
    """Read and format a STAR file.
    
    [WORKFLOW]
    1. Read STAR file using starfile library
    2. Handle both RELION 3.0 and 3.1 formats
    3. Convert empty key to 'particles' for 3.0 format
    
    [PARAMETERS]
    file_name : Union[str, Path]
        Path to the STAR file
        
    [OUTPUT]
    Dict[str, pd.DataFrame]
        Dictionary containing 'particles' DataFrame and optionally 'optics'
        
    [RAISES]
    StarFileError
        If file cannot be read or has invalid format
        
    [EXAMPLE]
    >>> star_data = format_input_star('run_data.star')
    >>> particles_df = star_data['particles']
    """
    try:
        star_file = starfile.read(file_name, always_dict=True)
        if '' in star_file:
            star_file['particles'] = star_file.pop('')
        return star_file
    except Exception as e:
        raise FormatError(f"Failed to read STAR file: {str(e)}")

def format_output_star(star_file: Dict[str, pd.DataFrame],
                       file_name: Union[str, Path]) -> None:
    """Write formatted data to a STAR file.

    This function writes all data blocks from the input dictionary to the
    output STAR file, ensuring compatibility with various STAR file formats,
    including multi-block files from RELION 5.

    [WORKFLOW]
    1. Validate that the input is a non-empty dictionary.
    2. Write all key-value pairs from the dictionary to the STAR file.

    [PARAMETERS]
    star_file : Dict[str, pd.DataFrame]
        Dictionary containing data blocks to be written.
    file_name : Union[str, Path]
        Output file path.

    [RAISES]
    StarFileError
        If writing fails or the input dictionary is empty.

    [EXAMPLE]
    >>> data = {'particles': particles_df, 'optics': optics_df}
    >>> format_output_star(data, 'output.star')
    """
    try:
        if not star_file:
            raise FormatError("Input dictionary is empty. Nothing to write.")

        starfile.write(star_file, file_name, overwrite=True)
    except Exception as e:
        raise StarFileError(f"Failed to write STAR file: {str(e)}")


def run_command(
    command: Union[List[str], str],
    log_path: Path,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    shell: bool = False,
    verbose: bool = True,
    module_load: Optional[Union[str, List[str]]] = None,
) -> None:
    """
    Runs a command, logs its output, and handles errors.

    Args:
        command: The command to run as a list or a single string.
        log_path: Path to the log file for stdout and stderr.
        cwd: The working directory for the command. Defaults to None.
        env: Environment variables for the command. Defaults to None.
        shell: Whether to use the shell. For complex commands or module loading,
               this will be forced to True.
        verbose: If True, prints command info to the main logger.
        module_load: A module or list of modules to load before running the command.
                     e.g., 'cryolo' or ['module1', 'module2'].
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    use_shell = shell or bool(module_load)
    if use_shell:
        cmd_str = ' '.join(map(str, command)) if isinstance(command, list) else command
        if module_load:
            modules = [module_load] if isinstance(module_load, str) else module_load
            load_prefix = '; '.join(f"module load {mod}" for mod in modules)
            executable_command = f"{load_prefix}; {cmd_str}"
        else:
            executable_command = cmd_str
    else:
        executable_command = command

    if verbose:
        log_cmd_str = executable_command if isinstance(executable_command, str) else ' '.join(map(str, executable_command))
        logging.info(f"Running command: {log_cmd_str}")
        if cwd:
            logging.info(f"Working directory: {cwd}")

    try:
        with open(log_path, 'a') as log_file:
            subprocess.run(
                executable_command,
                check=True,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                env=env,
                shell=use_shell,
            )
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with exit code {e.returncode}.")
        logging.error(f"Check the log for details: {log_path.resolve()}")
        raise
    except FileNotFoundError:
        cmd_name = command[0] if isinstance(command, list) else command.split()[0]
        logging.error(f"Command not found: {cmd_name}. Ensure it is in the system's PATH.")
        raise
