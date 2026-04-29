from flask import Blueprint

bp = Blueprint("recommendation", __name__)

from . import web
