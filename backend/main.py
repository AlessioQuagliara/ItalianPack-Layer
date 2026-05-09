# main.py
from flask import Flask, render_template

from core.config import Config

from spare_parts.routes import spare_parts
from after_sales.routes import after_sales
from auth.routes import auth

app = Flask(__name__)

app.config.from_object(Config)

app.register_blueprint(auth)
app.register_blueprint(after_sales)
app.register_blueprint(spare_parts)

@app.route("/")
def index():
    title = "index"
    return render_template("landing/index.html", title=title)

@app.errorhandler(404)
@app.errorhandler(500)
@app.errorhandler(401)
@app.errorhandler(403)
def handle_error(error):
    return render_template("error/error.html", error=error), error.code

#Dalla documentazione: development server, only for development, DON'T USE IN PRODUCTION
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8129)