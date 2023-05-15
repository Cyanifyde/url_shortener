import os
import json
from flask import request, render_template, redirect, url_for, session, flash, Blueprint
from datetime import datetime
import hashlib

app = Blueprint('auth', __name__)
now = datetime.now()

def load_db():
    with open('users.json', 'r') as file:
        return json.load(file)['users']

def save_db(users):
    with open('users.json', 'w') as file:
        json.dump({'users': users}, file)

def find_user(name):
    users = load_db()
    for user in users:
        if user['name'] == name:
            return user
    return None

def check_login():
    try:
        name = session["user"]["name"]
        user = find_user(name)
        if not user:
            session["access"] = "False"
            return False
        elif int(now.strftime("%d%H%M"))+30 <= int(session["user"]["time"]):
            session["access"] = "False"
            return False
        else:
            session["access"] = "True"
            return True
    except:
        session["access"] = "False"
        return False

def set_time():
    session["user"]["time"] = now.strftime("%d%H%M")


open_list = ["/","/login","/signup"]

@app.before_request 
def before_request_callback(): 
    if not check_login():
        path = request.path
        if path not in open_list:
            flash("Session is over")
            return redirect(url_for('auth.login'))
        else:
            session["access"] = "False"
    else: 
        set_time()

@app.route("/login")
def login():
    if session["access"] == "True":
        return redirect(url_for('index'))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def loginPOST():
    data = request.form
    name = data["name"]
    password = hashlib.sha256(data["password"].encode("utf-8")).hexdigest()
    user = find_user(name)
    if user:
        if password == user["password"]:
            session["user"] = {"name": name, "time": now.strftime("%d%H%M"), "power": user["power"]}
            session["access"] = "True"
            return redirect(url_for('index'))
        else:
            flash("wrong username/password")
            return redirect(url_for('auth.login'))
    else:
        flash("wrong username/password")
        return redirect(url_for('auth.login'))

    
@app.route("/signup")
def signup():
    return render_template("signup.html", access=session["access"])
    
@app.route("/signup", methods=["POST"])
def signupPOST():
    data = request.form
    name = data["name"]
    user = find_user(name)
    if not user:
        session["user"] = {"name": name, "time": now.strftime("%d%H%M"), "power": "1"}
        users = load_db()
        users.append({"name": name, "password": hashlib.sha256(data["password"].encode("utf-8")).hexdigest(), "power": 1})
        save_db(users)
        session["access"] = "True"
        return redirect(url_for('index'))
    else:
        flash("Username in use")
        return redirect(url_for('auth.signup'))

@app.route("/signout")
def signout():
    session["user"] = ""
    session["access"] = "False"
    return redirect("/")

@app.route("/change_password", methods=["POST"])
def change_password():
    data = request.form
    old_password_hash = hashlib.sha256(data["old-password"].encode("utf-8")).hexdigest()
    user = find_user(session["user"]["name"])
    if user and user["password"] == old_password_hash:
        if data["new-password"]:
            new_password_hash = hashlib.sha256(data["new-password"].encode("utf-8")).hexdigest()
            user["password"] = new_password_hash
            users = load_db()
            for i, u in enumerate(users):
                if u["name"] == user["name"]:
                    users[i] = user
                    break
            save_db(users)
            flash("password changed")
        else:
            flash("old password entered is incorrectly entered")
    else:
        flash("previous password is wrong")
    return redirect(url_for('auth.profile'))

@app.route("/wipedb", methods=["GET"])
def wipe():
    x=find_user(session["user"]["name"])
    if x["session"] == "2":
        save_db([])
    return redirect("/")
