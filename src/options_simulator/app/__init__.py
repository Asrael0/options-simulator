"""The simulator's web interface, built with NiceGUI.

This package depends on ``pricing``, never the other way round: the engine
stays usable from a notebook or any other frontend.
"""

from .main import main

__all__ = ["main"]
