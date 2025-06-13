#!/usr/bin/env python3
"""
Main entry point for Vast.ai Provisioning GUI with fbs
"""

import sys
import os

# Add the current directory to path to import our modules
sys.path.insert(0, os.path.dirname(__file__))

from fbs_runtime.application_context.PySide6 import ApplicationContext
from provisioning_gui import ProvisioningGUI


class AppContext(ApplicationContext):
    def run(self):
        # Initialize the main window with context
        self.main_window = ProvisioningGUI(app_context=self)
        self.main_window.show()
        return self.app.exec()
    
    def get_resource(self, *path_parts):
        """Get resource file path"""
        return super().get_resource(*path_parts)


if __name__ == '__main__':
    appctxt = AppContext()
    exit_code = appctxt.run()
    sys.exit(exit_code)