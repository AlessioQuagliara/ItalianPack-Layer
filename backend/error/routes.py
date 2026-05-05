# error/routes.py
from flask import Flask, flash, render_template, url_for, request, redirect, session, Blueprint

error = Blueprint('error', __name__)

@error.errorhandler(404)
def page_not_found(error):
    return render_template("error/404.html")

@error.errorhandler(500)
def server_error(error):
    return render_template("error/500.html")

@error.errorhandler(401)
def method_allowed(error):
    return render_template("error/401.html")