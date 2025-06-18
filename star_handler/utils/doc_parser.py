import re
from textwrap import dedent
from typing import Tuple

def parse_docstring(docstring: str) -> Tuple[str, str]:
    """Parses a docstring into a short help summary and a detailed epilog.

    [WORKFLOW]
    1. Dedents the docstring to handle indentation.
    2. Splits the docstring into a summary and an epilog based on the first blank line.
    3. The summary is the text before the first blank line.
    4. The epilog is the text after the first blank line.

    [PARAMETERS]
    docstring : str
        The input docstring, typically from a class or function's __doc__.

    [OUTPUT]
    Tuple[str, str]
        A tuple containing two strings: (help_summary, epilog).
        Returns ("", "") if the docstring is empty.
    
    [EXAMPLE]
    doc = \"\"\"This is the summary.
    
    This is the detailed epilog.
    \"\"\"
    help_summary, epilog = parse_docstring(doc)
    # help_summary -> "This is the summary."
    # epilog -> "This is the detailed epilog."
    """
    if not docstring:
        return "", ""

    docstring = dedent(docstring).strip()
    
    parts = re.split(r'\n\s*\n', docstring, 1)
    help_summary = parts[0].replace('\n', ' ').strip()
    
    if len(parts) > 1:
        epilog = parts[1].strip()
    else:
        epilog = ""
        
    return help_summary, epilog
