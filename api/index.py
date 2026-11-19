import os
import sys

# Ensure the root project directory is in the Python search path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

# Vercel WSGI entry point
handler = app