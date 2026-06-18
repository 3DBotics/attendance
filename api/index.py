import sys
import os

# Add the project root to the path so Flask app and models can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel expects the WSGI callable to be named `app`
# This file is the entry point for all serverless function invocations
