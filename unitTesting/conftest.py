"""
Adds the backend directory to sys.path so all test modules can import
from final backend modules without installation.
"""
import sys
import os

BACKEND = os.path.join(os.path.dirname(__file__), "..", "final", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))
