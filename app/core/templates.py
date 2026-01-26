from fastapi.templating import Jinja2Templates
from fastapi import Request
from app.core.csrf import get_csrf_token
import os
import sys

# Helper for PyInstaller path
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Initialize Templates
templates = Jinja2Templates(directory=resource_path("app/templates"))

# Inject CSRF token function into templates
def csrf_token_func(request: Request):
    return get_csrf_token(request)

templates.env.globals['csrf_token'] = csrf_token_func
