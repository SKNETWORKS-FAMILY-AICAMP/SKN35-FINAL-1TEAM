"""Compatibility import for the parser implementation in structured."""

import sys

from ..structured import docling_parser as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
