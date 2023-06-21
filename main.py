from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_bootstrap import Bootstrap #Importamos bootstrap
from flask_cors import CORS
from flask_wtf import FlaskForm
from wtforms.fields import StringField, PasswordField, SubmitField, SelectField
from wtforms import validators
import requests
import time
import os

BASE_URL = "cloudx.safeuem.com"
HEADERS ={"content-type":"application/json"}


app = Flask(__name__)
bootstrap = Bootstrap(app) #Toma la app de Flask y así se instancia Bootstrap
CORS(app)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY


class LoginForm(FlaskForm):
    safeuem_user = StringField("Username", [validators.input_required(), validators.length(max=25)])
    username = StringField("Workspace name", [validators.input_required(), validators.length(max=25)])
    password = PasswordField("Password",[validators.input_required(), validators.length(max=25)])
    submit = SubmitField("Log in")
    

class OptionFile(FlaskForm):
    option = SelectField('Select the option:', choices=[('bulk', 'Bulk Devices (CSV File)'), ('single', 'Single Device')])
    submit = SubmitField("Next")


@app.route('/', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    context = {
        "login_form" : login_form
    }
    if login_form.validate_on_submit():
        username = login_form.username.data #Get Username
        password = login_form.password.data #Get Password
        safeuem_user = login_form.safeuem_user.data #Get SafeUEM user   
        response = login_request(user=str(username), password=str(password), server=str(safeuem_user))#Login Request
        print("Response", response.status_code)
        if response.status_code >= 400:
            flash("Wrong credentials")
            return redirect(url_for('login'))
        else:
            cookie = response.cookies.get_dict()
            session['token'] = cookie['token']
            return redirect(url_for('move'))
    
    return render_template('login.html', **context)

@app.route('/move', methods=['GET', 'POST'])
def move():
    option_file = OptionFile()
    context = {
        "option_file": option_file
    }
    if option_file.validate_on_submit():
        option = option_file.option.data #Get data from selector
        if option == "bulk":
            return redirect(url_for('bulk'))
        else :
            return redirect(url_for('single'))        
    
    return render_template('move.html', **context)

@app.route('/unlock')
def unlock():
    return render_template('unlock.html')

@app.route('/enroll')
def enroll():
    return render_template('enroll.html')

@app.route('/unenroll')
def unenroll():
    return render_template('unenroll.html')

@app.route('/bulk')
def bulk():
    return render_template('bulk.html')
@app.route('/single')
def single():
    return render_template('single.html')

def login_request(user, password, server):
    url = f"https://{server}.{BASE_URL}/partner/login"
    body = {"username": user, "password": password}
    response = create_request(url, HEADERS, request_type="post", data = body)
    return response


def create_request(url, headers, request_type, data=None, cookies = None):
    """
    Function to make a request to the server
    """
    
    request_func = getattr(requests, request_type)
    kwargs = {"url": url, "headers": headers, "cookies":cookies}
    if request_type == "post" or request_type == "put":
        kwargs["json"] = data
    try:
        req = request_func(**kwargs)
        return req
    except Exception as e:
        print("[ERROR] There was an error with the request, details:")
        print(e)
        
        return None
    


if __name__ == "__main__":
    app.run(debug=True)