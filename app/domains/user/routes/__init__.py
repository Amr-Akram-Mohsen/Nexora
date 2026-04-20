from flask import Blueprint

bp = Blueprint("user", __name__)

from . import web
from . import admin
from . import api
