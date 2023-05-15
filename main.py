import json
import hashlib
import time
from urllib.parse import urlsplit, urlunsplit, quote
import uuid
import threading
from flask import Flask, request, render_template, redirect, url_for , session
import validators
import os
app = Flask(__name__)

######settings######
host="0.0.0.0"
port=8080
debug=False

json_save_time= 2 * 60
json_file="data.json"

default_scheme="https://"

hash_length=5 # half the length ie 5 will give a length of 10

app.secret_key = "euwhfewf"

cache_timeout= 5*60

####################
def check_session():
    try:
        x=session["access"]
    except KeyError:
        session["access"]="False"

def remove_scheme(url):
    parsed_url = urlsplit(url)
    return urlunsplit(("", parsed_url.netloc, parsed_url.path, parsed_url.query, parsed_url.fragment))

class urlShorteneren:
    def __init__(self, file):
        self.file=file
        self.data={}
        self.cache={}
        self.read(file)
        self.save_thread=threading.Thread(target=self.save)
        self.save_thread.start()
        
    def read(self,file):
        with open(file,"r",encoding="UTF-8") as f:
            self.data=json.load(f)
            
    def save(self):
        while True:
            with open(self.file,"w",encoding="UTF-8") as f:
                json_object = json.dumps(self.data, indent=4)
                f.write(json_object)
            self._check_and_remove_users()
            self._cut_cache()
            time.sleep(json_save_time)

    def _cut_cache(self, max= 10):
        for user in self.cache:
            if time.time()-user["time"]>cache_timeout:
                del self.cache[user]
        if len(self.cache)>max:
            x=list(self.cache.keys())[len(self.cache)-max:]
            for i in x:
                del self.cache[i]
        
    def _add(self, url, shortened, version=1):
        if url not in self.data:
            self.data[url]={}
            self.data[url]["hash"]=""
            self.data[url]["custom"]=[]
            self.data[url]["uuid"]=""
            self.data[url]["created"]=str(time.time())
            self.data[url]["userList"] = []
        if version == 1:
            if self.data[url]["hash"] == "":
                self.data[url]["hash"]=shortened
        elif version == 2:
            if not shortened in self.data[url]["custom"]:
                self.data[url]["custom"].append(shortened)
        elif version == 3:
            if self.data[url]["uuid"] == "":
                self.data[url]["uuid"]=shortened
        else:
            return False
        
    def add_user(self, url, user_id, guest=False):
        if url in self.data:
            self.data[url]["userList"].append({
                "user_id": user_id,
                "created": time.time(),
                "guest": guest
            })
    
    def remove_user(self, url, user_id):
        url=urlShortener.find_url(url)
        if url in self.data:
            for user in self.data[url]["userList"]:
                if user["user_id"]["name"] == user_id:
                    self.data[url]["userList"].remove(user)

    
    def find_urls_by_user(self, user_id, cache=True, save_to_cache=True):
        if cache:
            if user_id in self.cache:
                return self.cache[user_id]["urls"]
        urls = []
        for url, data in self.data.items():
            for user in data["userList"]:
                if user["user_id"]["name"] == user_id:
                    urls.append({"hash": data["hash"], "url": url,"uuid":data["uuid"],"custom":data["custom"]})
        if save_to_cache:
            self.cache[user_id]={"urls":urls,"time":time.time()}

        return urls
    
    def _check_and_remove_users(self):
        try:
            for url in self.data.copy():
                for user in self.data[url]["userList"]:
                    if (user["guest"] and time.time() - user["created"] > 1 * 60):
                      
                        self.remove_user(url, "Guest")
                if len(self.data[url]["userList"]) == 0:
                    del self.data[url]
        except RuntimeError:
            pass

    def create(self, url, version=1, data=str()):
        if url not in self.data:
            if validators.url(url):
                url=remove_scheme(url)
                hashed=hashlib.shake_256(url.encode()).hexdigest(hash_length)
                
                self._add(url, hashed)
                i_d=str(uuid.uuid5(uuid.NAMESPACE_URL, url))
                self._add(url, i_d, version=3)
                if version == 1:
                    return hashed
                elif version == 3:
                    return i_d
                elif version == 2:
                    if data == "":
                        return False
                    elif isinstance(data, str):
                        safe=quote(data)
                        self._add(url, safe, 2)
                        return safe
                else:
                    return False
            else:
                return False
            
    def find_url(self,uinput):
        for url in self.data:
            if uinput == self.data[url]["hash"]:
                return url
            elif uinput == self.data[url]["uuid"]:
                return url
            else:
                safe=quote(uinput)
                if safe in self.data[url]["custom"]:
                    return url
        return False

urlShortener=urlShorteneren(json_file)

@app.route('/', methods=['GET'])
def index():
    check_session()
    try:
        return render_template("index.html",access=session["access"])
    except KeyError:
        return render_template("index.html",access="False")

@app.route('/create', methods=['POST','GET'])
def create():
    check_session()
    if request.method == 'POST':
        url=request.form["url"]
        version=request.form["version"]
        data=request.form["data"]
        if urlShortener.find_url(data):
            return redirect(url_for("index"))
        elif url == "":
            return redirect(url_for("index"))
        else:
            hashed=urlShortener.create(url, version=int(version), data=data)
            try:
                if session["access"]:
                    urlShortener.add_user(remove_scheme(url), session["user"], guest=False)
                else:
                    urlShortener.add_user(remove_scheme(url), "Guest", guest=True)
            except KeyError:
                urlShortener.add_user(remove_scheme(url), "Guest", guest=True)
            if hashed is False:
                return redirect(url_for("index"))
            return redirect(url_for("show", url=hashed))
    else:
        return redirect(url_for("index"))
    
@app.route('/show/<string:url>', methods=['GET'])
def show(url):
    if url != "":
        found=urlShortener.find_url(url)
        if url:
            return render_template("show.html",url=url, found=found)
        else:
            return redirect(url_for("index"))
    else:
        return redirect(url_for("index"))


@app.route('/user', methods=['GET'])
def user():
    check_session()
    try:
        if session["access"]:

            user_urls = urlShortener.find_urls_by_user(session["user"]["name"])
            return render_template("user.html", user=session["user"], urls=user_urls)
        else:
            return redirect(url_for("index"))
    except KeyError:
        return redirect(url_for("index"))
    
@app.route('/delete/<string:url>', methods=['GET'])
def delete(url):
    try:
        if session["access"]:
            urlShortener.remove_user(url, session["user"]["name"])
            return redirect(url_for("user"))
        else:
            return redirect(url_for("index"))
    except KeyError:
        return redirect(url_for("index"))
    
@app.route('/<string:url>', methods=['GET'])
def redirect_url(url):
    found=str(urlShortener.find_url(url))
    found=default_scheme+found
    if found:
        return render_template("redirect.html", url=found)
    else:
        return redirect(url_for("index"))

from auth.auth import app as auth
app.register_blueprint(auth)
if __name__ == '__main__':
    app.run(host=host,port=port, debug=debug)
