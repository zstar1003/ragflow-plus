import os


def get_root_folder():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
