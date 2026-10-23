import os
import sys

root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

import importlib
_backend_models = importlib.import_module("backend.models")
sys.modules[__name__] = _backend_models
from backend.models import *
