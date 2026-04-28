"""
Adds the backend directory to sys.path so all test modules can import
from fetcher/, analyzer/, and chat/ without installation.
"""
import sys
import os

BACKEND = os.path.join(os.path.dirname(__file__), "..", "prototypes", "sally", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))
