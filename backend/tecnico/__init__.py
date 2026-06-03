from flask import Blueprint

tecnico_bp = Blueprint('tecnico', __name__, url_prefix='/tecnico')

# Import dopo la definizione del Blueprint per evitare circular import
from tecnico import ordini, documenti, rda, scontrini  # noqa: F401, E402
