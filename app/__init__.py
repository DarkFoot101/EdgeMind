"""EdgeMind Package Header"""

from pathlib import Path

__version__ = "2.0.2"

# Enforce strict package path boundary to prevent collision with workspace 'app/' directories
__path__ = [str(Path(__file__).resolve().parent)]
