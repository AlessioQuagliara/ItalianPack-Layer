from flask import Blueprint

magazzino_bp = Blueprint('magazzino', __name__, url_prefix='/magazzino')

from magazzino import routes  # noqa: F401, E402
