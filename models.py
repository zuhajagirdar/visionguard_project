import importlib, sys
_backend_models = importlib.import_module('backend.models')
sys.modules[__name__] = _backend_models
