# main.py
from flask import Flask, abort, flash, render_template, url_for, request, redirect, session
from flask_login import LoginManager, login_user
import unicodedata
from urllib.parse import (
    ParseResult, SplitResult, _coerce_args, _splitnetloc, _splitparams,
    scheme_chars, urlencode as original_urlencode, uses_params,
)

app = Flask(__name__)

app.secret_key = "mcadiosncioa"

login_manager = LoginManager()

@app.route("/")
def index():
    title = "Home"
    return render_template("landing/home.html", title=title)


@app.route("/login", methods=['GET', 'POST'])
def login():
    title = "Login"
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "Alessio" and password == "ciao":
            return "Login successful!"
        else:
            error = "invalid credentials"
    
    return render_template("landing/login.html", title=title, error=error)


@app.errorhandler(404)
def page_not_found(error):
    return render_template("landing/error/404.html")

@app.errorhandler(500)
def server_error(error):
    return render_template("landing/error/500.html")


#Dalla documentazione: development server, only for development, DON'T USE IN PRODUCTION
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8129)