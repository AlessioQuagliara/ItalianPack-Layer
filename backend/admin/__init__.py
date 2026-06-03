from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Import dopo la definizione del Blueprint per evitare circular import
from admin import dashboard, utenti, ordini, documenti, rda, scontrini, sync, furgoni, analisi  # noqa: F401, E402
