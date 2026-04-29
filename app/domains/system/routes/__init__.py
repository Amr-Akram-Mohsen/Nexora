from flask import Blueprint

bp = Blueprint("system", __name__)

from . import web
