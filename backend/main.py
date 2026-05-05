# main.py
from flask import Flask, flash, render_template, url_for, request, redirect, session, Blueprint

app = Flask(__name__)

app.secret_key = "mcadiosncioa"

@app.route("/")
def index():
    title = "index"
    return render_template("landing/index.html", title=title)


#Dalla documentazione: development server, only for development, DON'T USE IN PRODUCTION
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8129)