from flask import Flask, render_template, request, session, jsonify
import pusher
import urllib
from datetime import datetime
import httpagentparser
import json
import os
import hashlib
from dbsetup import create_connection, create_session, update_or_create_page, select_all_sessions, select_all_user_visits, select_all_pages

app = Flask(__name__)
app.secret_key = os.urandom(24)

# configure pusher object
pusher = Pusher(
app_id='833071',
key='f55e5418eacd8f2ed633',
secret='2d6c610ba80b812648aa',
cluster='ap2',
ssl=True)

database = "./pythonsqlite.db"
conn = create_connection(database)
c = conn.cursor()

userOS = None
userIP = None
userCity = None
userBrowser = None
userCountry = None 
userContinent = None
sessionID = None

def main():
    global conn, c

def parseVisitor(data):
    update_or_create_page(c,data)
    pusher.trigger(u'pageview', u'new', {
            u'page': data[0],
            u'session': sessionID,
            u'ip': userIP
        })
    pusher.trigger(u'numbers', u'update', {
            u'page': data[0],
            u'session': sessionID,
            u'ip': userIP
        })

@app.before_request
def getAnalyticsData():
    global userOS, userBrowser, userIP, userContinent, userCity, userCountry,sessionID
    userInfo = httpagentparser.detect(request.headers.get('User-Agent'))
    userOS = userInfo['platform']['name']
    userBrowser = userInfo['browser']['name']
    userIP = "72.229.28.185" if request.remote_addr == '127.0.0.1' else request.remote_addr
    api = "https://www.iplocate.io/api/lookup/" + userIP
    try:
        resp = urllib.request.urlopen(api)
        result = resp.read()
        result = json.loads(result.decode("utf-8"))
        userCountry = result.get('country','')
        userContinent = result.get('continent','')
        userCity = result.get('city','')
    except:
        print("Could not find: ", userIP)
    getSession()

def getSession():
    """
    Get user session details
    """
    global sessionID
    time = datetime.now().replace(microsecond=0)
    if 'user' not in session:
        lines = (str(time)+userIP).encode('utf-8')
        session['user'] = hashlib.md5(lines).hexdigest()
        sessionID = session['user']
        pusher.trigger(u'session', u'new', {
            u'ip': userIP,
            u'continent': userContinent,
            u'country': userCountry,
            u'city': userCity,
            u'os': userOS,
            u'browser': userBrowser,
            u'session': sessionID,
            u'time': str(time),
        })
        data = [userIP, userContinent, userCountry, userCity, userOS, userBrowser, sessionID, time]
        create_session(c,data)
    else:
        sessionID = session['user']

@app.route('/')
def index():
    data = ['home', sessionID, str(datetime.now().replace(microsecond=0))]
    parseVisitor(data)
    return render_template('index.html')

@app.route('/about')
def about():
    data = ['about',sessionID, str(datetime.now().replace(microsecond=0))]
    parseVisitor(data)
    return render_template('about.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/dashboard/<session_id>', methods=['GET'])
def sessionPages(session_id):
    result = select_all_user_visits(c,session_id)
    return render_template("dashboard-single.html",data=result)

@app.route('/get-all-sessions')
def get_all_sessions():
    """
    Getting all the session details of the user
    """
    data = []
    dbRows = select_all_sessions(c)
    for row in dbRows:
        data.append({
            'ip' : row.get('ip',''),
            'continent' : row.get('continent',''),
            'country' : row.get('country',''),
            'city' : row.get('city',''),
            'os' : row.get('os',''),
            'browser' : row.get('browser',''),
            'session' : row.get('session',''),
            'time' : row.get('created_at','')
        })
    return jsonify(data)

if __name__ == '__main__':
    main()
    app.run(debug=True)
