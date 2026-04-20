from flask import Blueprint

bp = Blueprint("interaction", __name__)

from . import web
from . import admin
from . import api
