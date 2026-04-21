from flask import Blueprint

bp = Blueprint("item", __name__)

from . import web
from . import api
