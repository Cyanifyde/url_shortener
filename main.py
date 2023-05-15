import json
import hashlib
import time
from urllib.parse import urlsplit, urlunsplit, quote
import uuid
import threading
from flask import Flask, request, render_template, redirect, url_for , session
import validators

def remove_scheme(url):
    parsed_url = urlsplit(url)
    return urlunsplit(("", parsed_url.netloc, parsed_url.path, parsed_url.query, parsed_url.fragment))

class urlShorteneren:
    def __init__(self, file):
        self.file=file
        self.data={}
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
                print("Saved")
            time.sleep(150)
            
    def _add(self, url, shortened, version=1):
        if url not in self.data:
            self.data[url]={}
            self.data[url]["hash"]=""
            self.data[url]["custom"]=[]
            self.data[url]["uuid"]=""
            self.data[url]["visits"]=0
            self.data[url]["created"]=str(time.time())
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

    def create(self, url, version=1, data=str()):
        if url not in self.data:
            if validators.url(url):
                url=remove_scheme(url)

                hashed=hashlib.shake_256(url.encode()).hexdigest(5)
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
                self.data[url]["visits"]+=1
                return url
            elif uinput == self.data[url]["uuid"]:
                self.data[url]["visits"]+=1
                return url
            else:
                safe=quote(uinput)
                if safe in self.data[url]["custom"]:
                    self.data[url]["visits"]+=1
                    return url
        return False

urlShortener=urlShorteneren("data.json")

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")

@app.route('/create', methods=['POST','GET'])
def create():
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
    
@app.route('/<string:url>', methods=['GET'])
def redirect_url(url):
    found=str(urlShortener.find_url(url))
    found="https://"+found
    if found:
        return render_template("redirect.html", url=found)
    else:
        return redirect(url_for("index"))
    
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8080, debug=False)
