import logging
logging.getLogger(__name__).addHandler(logging.NullHandler)

from .lib import Task, TaskLib
from .lib import DEFAULT_CONFIG as config
from .lib import TASK_OK, TASK_ERROR, TASK_EXTENSION_ERROR
from .lib import make_uid

__version__ = '1.0.0dev'
