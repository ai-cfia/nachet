"""Stop the test worker after MongoDB contains the imported samples."""

import os
import signal
import sys
from pathlib import Path

import fiftyone as fo

from register_fiftyone import register_fiftyone

original_import = fo.Dataset.add_dir


def interrupted_import(dataset, *args, **kwargs):
    original_import(dataset, *args, **kwargs)
    Path(sys.argv[4]).write_text(dataset.name)
    os.kill(os.getpid(), signal.SIGKILL)


fo.Dataset.add_dir = interrupted_import
register_fiftyone(sys.argv[1], Path(sys.argv[2]), sys.argv[3])
