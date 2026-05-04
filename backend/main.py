# main.py
from flask import Flask, render_template, url_for, request, redirect

app = Flask(__name__)

@app.route("/")
def index():
    title = "Home"
    return render_template("landing/home.html", title=title)

@app.route("/login", methods=['GET', 'POST'])
def login():
    error = None
    title = "Login"
    if request.method == 'POST':
        if valid_login(
            request.form['username'],
            request.form['password']): 
            return log_the_user_in(request.form['username'])
        else
    return render_template("landing/login.html", title=title)

@app.errorhandler(404)
def page_not_found(error):
    return render_template("landing/error/404.html")

@app.errorhandler(500)
def server_error(error):
    return render_template("landing/error/500.html")


#Dalla documentazione: development server, only for development, DON'T USE IN PRODUCTION
if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=8000)