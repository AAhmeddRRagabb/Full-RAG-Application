# ----------------------------------------------
# Base Controller Module
# ----------------------------------------------

import helpers.config as CFG
import os

class BaseController:

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))

        # assets dir
        self.assests_files_path = os.path.join(self.base_dir, "assets/files")
        os.makedirs(self.assests_files_path, exist_ok = True) 

        