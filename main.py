from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_bootstrap import Bootstrap #Importamos bootstrap
from flask_cors import CORS
from flask_wtf import FlaskForm
from wtforms.fields import StringField, PasswordField, SubmitField, SelectField, RadioField
from wtforms import validators
from fileinput import filename
import requests
import shutil
import time
import os
import zero_touch_api
from read_csv import read_csv
from flask_login import logout_user


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

class MoveSingleDevice(FlaskForm):
    device_identifier = StringField("Device identifier", [validators.input_required(), validators.length(max=25)])
    to_group = SelectField("To group: ", coerce=str)
    submit = SubmitField("Send request")
    
class EnrollSingleDevice(FlaskForm):
    device_identifier = StringField("Device IMEI", [validators.input_required(), validators.length(max=25)])
    configuration = SelectField("Configuration: ", coerce=str)
    submit = SubmitField("Send request")

class EnrollBulkDevice(FlaskForm):
    configuration = SelectField("Configuration: ", coerce=str)
    
class UnenrollSingleDevice(FlaskForm):
    device_identifier = StringField("Device IMEI", [validators.input_required(), validators.length(max=25)])
    delete = RadioField("Delete device from", choices=[('zt','Zero Touch'),('zt&sf', 'Zero Touch and SafeUEM')],  default='zt')
    submit = SubmitField("Unenroll device")


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
        if response.status_code >= 400:
            flash("Wrong credentials")
            return redirect(url_for('login'))
        else:
            cookie = response.cookies.get_dict()
            service = zero_touch_api.get_credentials_account()
            list_of_customers = zero_touch_api.get_list_of_customers()
            customer_id = zero_touch_api.get_customer_id("Nexa", list_of_customers)
            with open(f'user_credential_{customer_id}.json', 'w') as f:
                print(f)
          #  tos = zero_touch_api.tos_error(customer_id)
          #  print(tos)
            configurations = zero_touch_api.get_configurations(customer_id)
            session['customer_id'] = customer_id
            session['configurations'] = configurations
            session['token'] = cookie['token']
            session['server'] = safeuem_user
            return redirect(url_for('single_move'))
    
    return render_template('login.html', **context)

@app.route('/logout', methods=['GET','POST'])
def logout():
    logout_user() #Delete session cookies
    os.remove("./user_credential.json")    
    return redirect(url_for('login'))

@app.route('/single/enroll', methods=['GET', 'POST'])
def single_enroll():
    enroll_single_device_form = EnrollSingleDevice()
    token = session.get('token')
    server = session.get('server')
    list_of_customers = zero_touch_api.get_list_of_customers()
    customer_id = zero_touch_api.get_customer_id("Nexa", list_of_customers)
    configurations = zero_touch_api.get_configurations(customer_id)
    enroll_single_device_form.configuration.choices = configurations
    context = {
        "enroll_single_device_form": enroll_single_device_form
    }  
    if enroll_single_device_form.validate_on_submit():
        imei = enroll_single_device_form.device_identifier.data # Get IMEi
        configuration = enroll_single_device_form.configuration.data #Get Config
        claim = zero_touch_api.claim_device(imei, customer_id)
        set_configuration = zero_touch_api.set_configuration(configuration, claim, customer_id)
        return redirect(url_for('single_enroll'))



    return render_template('single_enroll.html', **context)

@app.route('/bulk/enroll', methods = ['GET', 'POST'])
def bulk_enroll():

    server = session.get('server')
    token = session.get('token')
    list_of_customers = zero_touch_api.get_list_of_customers()
    customer_id = zero_touch_api.get_customer_id("Nexa", list_of_customers)
    configurations = zero_touch_api.get_configurations(customer_id)
    context = {
        "configurations": configurations
    } 
    if request.method == 'POST': 
        try:
            f = request.files['csvFile']
            f.save(f'./files/{f.filename}')
            imeis = read_csv(f'./files/{f.filename}')
            configuration = request.form.get('conf_select')   
            default_configuration = zero_touch_api.set_default_configuration(configuration, customer_id)
            bulk_json = zero_touch_api.build_bulk_json(customer_id, imeis)
            claims = zero_touch_api.claim_batch_devices(bulk_json)      
            path = os.path.join(f'./files', f.filename)  
            os.remove(path)
    
        except(FileNotFoundError) as error:
            print(error)
        
        
    return render_template('bulk_enroll.html', **context)

@app.route('/single/unenroll', methods=['GET', 'POST'])
def single_unenroll():
    single_unenroll_form = UnenrollSingleDevice()
    context = {
        "single_unenroll_form" : single_unenroll_form
        
    }
    if single_unenroll_form.validate_on_submit():
        choice = single_unenroll_form.delete.data
        if choice == 'zt':
            imei = single_unenroll_form.device_identifier.data #Get IMEI
            unclaim = zero_touch_api.unclaim_single_device(imei)
            return redirect(url_for('single_unenroll'))        
        else:
            return redirect(url_for('single_unenroll')) 
        
        
    return render_template('single_unenroll.html', **context)

@app.route('/bulk/unenroll', methods = ['GET', 'POST'])
def bulk_unenroll():
    server = session.get('server')
    token = session.get('token')
    if request.method == 'POST': 
        try:
            option = request.form.getlist('delete_options')
            print(option)
            f = request.files['csvFile']
            f.save(f'./files/{f.filename}') 
            imeis = read_csv(f'./files/{f.filename}')
            if option[0] == 'zt':
                unclaim_json = zero_touch_api.build_bulk_unclaim_json(imeis)
                print(unclaim_json)

                unclaim_response = zero_touch_api.unclaim_batch_devices(unclaim_json)
            else:
                print("Deleting")
            path = os.path.join(f'./files', f.filename)  
            os.remove(path)
 
        except(FileNotFoundError) as error:
            print(error)
        
        
    return render_template('bulk_unenroll.html')

@app.route('/bulk/move', methods=['GET', 'POST'])
def bulk_move():
    server = session.get('server')
    token = session.get('token')
    if request.method == 'POST': 
        try:
            f = request.files['csvFile']
            f.save(f'./files/{f.filename}') 
            file_id = update_file_to_safeuem(f.filename, token, server)   
            response = move_bulk_devices(file_id, token, server)
            path = os.path.join(f'./files', f.filename)  
            os.remove(path)
            print(response)                
 
        except(FileNotFoundError) as error:
            print(error)
        
        
    return render_template('bulk_move.html')

@app.route('/single/move', methods=['GET', 'POST'])
def single_move():
    server = session.get('server')
    token = session.get('token')
    groups = get_groups_request(server, token)
    options = get_properties_from_groups(groups)
    move_single_device = MoveSingleDevice()
    move_single_device.to_group.choices = options
    context = {
        "move_single_device" : move_single_device
    }
    if move_single_device.validate_on_submit():
        device_identifier = move_single_device.device_identifier.data # Get imei
        to_group = move_single_device.to_group.data #To group
        response = get_device_request(device_identifier, token, server)
        if response["total"] == 0:
            flash("Device not found")
            return redirect(url_for('single_move'))
        else:
            ids, from_group = get_device_id_group(response["devices"][0])
            move = move_request(ids, from_group, to_group, token, server)
            if move != 200:
                flash("Error moving the device")
                return redirect(url_for('single_move'))
            else :
                return redirect(url_for('single_move'))                  
    
        
    
    return render_template('single_move.html', **context)

def move_bulk_devices(file_id, token, server):
    url = f"https://{server}.{BASE_URL}/partner/device/moveBatch"
    cookies = {"token": token}
    body = {"by" : "iMEI", "file" : file_id}
    response = create_request(url, HEADERS, "put", data = body, cookies=cookies)
    return response.json()
    

def update_file_to_safeuem( file_name, token, server):
    url = f"https://{server}.{BASE_URL}/partner/temp/moveBatch"
    cookies = {"token": token}
    multipart_form_data = {
        'filename' : open(f'./files/{file_name}', 'rb')       
    }
    response = requests.post(url, files=multipart_form_data, cookies= cookies)
    return response.json()["fileIds"][0]


def get_device_id_group(device_json):
    return [device_json["id"]], device_json["groups"][0]
    

def get_device_request(keyword, token, server):
    url = f"https://{server}.{BASE_URL}/partner/device/search?group=&by=others&keyword={keyword}"
    cookies = {"token": token}
    response = requests.get(url, cookies = cookies)
    return response.json()

def move_request(ids_devices, from_group, to_group, token, server):
    url = f"https://{server}.{BASE_URL}/partner/device/move"
    body = {"from" : from_group, "ids" : ids_devices,"to" : to_group}
    cookies = {"token": token}
    response = create_request(url, HEADERS, "put", data = body, cookies=cookies)
    return response.status_code

def get_properties_from_groups(groups):    
    return [(group["id"], group["name"]) for group in groups]           
            
def get_groups_request(server, token):
    url = f"https://{server}.{BASE_URL}/api/deviceGroup?deviceCount=false"
    cookies = {"token": token}
    response = requests.get(url, cookies = cookies)    
    return response.json()["groups"]

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
    uvicorn.run("main:app", host="0.0.0.0",
                port=int(os.environ.get("PORT", 8000)))