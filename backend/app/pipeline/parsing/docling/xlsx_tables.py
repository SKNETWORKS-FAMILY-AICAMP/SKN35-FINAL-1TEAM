"""Compatibility import for the parser implementation in structured."""

import sys

from ..structured import xlsx_tables as _implementation

sys.modules[__name__] = _implementation
