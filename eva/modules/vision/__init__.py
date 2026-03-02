from .watcher import CameraService
from .identifier import Identifier
from .webcam import Webcam
from .describer import Describer

# Backward compatibility — loader.py and wslclient.py import Watcher
Watcher = CameraService
