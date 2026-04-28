from flask import Blueprint

bp = Blueprint("content", __name__)

from . import web
from . import api
