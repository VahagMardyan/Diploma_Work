"""Backward-compatible measured-power export command.

Use ``extractor.py`` for the complete row-export interface. This wrapper retains
the historical utility name while delegating all work to the shared implementation.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import Optional

from extractor import main as export_main


def print_getter_usage() -> None:
    """Print usage example for the quick target exporter."""
    print("""
================================================================================
 GETTER UTILITY USAGE EXAMPLES (Quick Target Exporter)
================================================================================
Usage:
  python getter.py <source_csv> <output_file> --row <index>

Example:
  Extract measured target values (Dynamic, Leakage, Total Power) for row 0:
    python getter.py ../Datasets/dataset_power.csv Test/real_power.json --row 0
================================================================================
""")


def main(arguments: Optional[Sequence[str]] = None) -> int:
    """Export measured targets by forwarding to :mod:`extractor`."""
    provided_arguments = list(sys.argv[1:] if arguments is None else arguments)

    # Display clean usage text if run without arguments or with -h/--help
    if not provided_arguments or provided_arguments[0] in ("-h", "--help"):
        print_getter_usage()
        return 0

    if "--selection" not in provided_arguments:
        provided_arguments.extend(["--selection", "targets"])

    return export_main(provided_arguments)


if __name__ == "__main__":
    raise SystemExit(main())
