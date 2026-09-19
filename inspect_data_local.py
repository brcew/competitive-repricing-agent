"""
Utility to inspect seeded data (SQLite version).
"""

import os
os.environ['USE_LOCAL_CONFIG'] = '1'

import config
import config_local
config.settings = config_local.settings

from inspect_data import inspect_database

if __name__ == "__main__":
    print("🔧 Using SQLite database\n")
    inspect_database()