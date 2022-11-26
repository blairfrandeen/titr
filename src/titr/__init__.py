import os

__version__ = "0.9.0"
__db_user_version__ = 2

CONFIG_FILE: str = os.path.join(os.path.expanduser("~"), ".titr", "titr.cfg")
TITR_DB: str = os.path.join(os.path.expanduser("~"), ".titr", "titr.db")
