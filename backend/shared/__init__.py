from flask import Blueprint

shared_bp = Blueprint('shared', __name__, url_prefix='')

from shared import routes  # noqa: F401, E402
