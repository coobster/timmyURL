from flask import Flask, redirect, request, g, escape, abort, url_for
from sqlite3 import connect
from os.path import exists
from time import time
from hashlib import shake_128
from base64 import urlsafe_b64encode

DATABASE = "tinyURL.db"

app = Flask(__name__)

def make_url():
	while True:
		# first generate a random url key
		tmp = urlsafe_b64encode(shake_128(str(time()).encode()).digest(4)).strip(b'=').decode('utf-8')
		# test to see if it exists and if not then try another until one that does not exist is found
		if query('SELECT COUNT(*) FROM link WHERE turl=?',(tmp,)).fetchone()[0] == 0:
			return tmp

def setup():
	# if the database is not present create a new one.
	if not exists(DATABASE):
		sql = ["CREATE TABLE link (turl,lurl,stamp)","CREATE TABLE visit (turl,ip,stamp)"]
		db = connect(DATABASE)
		cur = db.cursor()
		for i in range(len(sql)):
			db.execute(sql[i],())
			print('CREATED: {}'.format(sql[i]))
		db.commit()
		db.close()

def get_db():
	db = getattr(g,'_database',None)
	if db is None:
		db = connect(DATABASE)
	return db

def query(sql,args):
	cur = get_db().cursor()
	r = cur.execute(sql,args)
	return r

# all the routes in the app
@app.route('/')
def index():
	ref = request.referrer                                                              
	if not ref:
		ref = 'https://'
	return '''
		<form action="/add" method="POST"><input name="url_input" value="{}"><input type='submit' text="add"></form>
	'''.format(ref)

@app.route('/<data>')
def link(data):
	with get_db() as db:
		cur = db.cursor()
		cur.execute('INSERT INTO visit VALUES(?,?,?)',(data,request.remote_addr,time()))
		db.commit()
		r = cur.execute('SELECT lurl FROM link WHERE turl=?',(data,))
		url = r.fetchone()
		if url:
			return redirect(url[0])
		else:
			return redirect(url_for('index'))

@app.route('/add',methods=["GET","POST"])
def add():
	if request.method == 'POST':
		tiny_url = make_url()
		long_url = escape(request.form['url_input'])
		test = query('SELECT turl FROM link WHERE lurl=?',(long_url,)).fetchone()
		if not test:
			with connect(DATABASE) as db:
				cur = db.cursor()
				cur.execute("INSERT INTO link VALUES(?,?,?)",(tiny_url,long_url,time()))
				db.commit()
		else:
			return "THE URL FOR {l} is :<a href=\"{t}\">{h}/{t}</a>".format(l=long_url,t=test[0],h=request.host)
		return "ADDED {l}: <a href=\"{t}\">{h}/{t}</a>".format(t=tiny_url,l=long_url,h=request.host)
		
	return abort(404)

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        #db.commit()
        db.close()

if __name__ == '__main__':
	setup()
	app.run()
