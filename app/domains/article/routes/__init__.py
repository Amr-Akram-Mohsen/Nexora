from flask import Blueprint

bp = Blueprint("article", __name__)

from . import web
from . import api
