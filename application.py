import os

from flask import Flask, session, render_template, request, flash, url_for, redirect, g
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from passlib.hash import sha256_crypt

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False #I switched to true
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Create tables
sqls = [
"CREATE TABLE users(id SERIAL NOT NULL PRIMARY KEY, username VARCHAR NOT NULL, password VARCHAR NOT NULL, email VARCHAR NOT NULL);",
"CREATE TABLE books(id SERIAL NOT NULL PRIMARY KEY, isbn VARCHAR UNIQUE NOT NULL, title VARCHAR NOT NULL, author VARCHAR NOT NULL, publication INTEGER NOT NULL, review_count INTEGER , average_score INTEGER NOT NULL);",
"CREATE TABLE reviews(id SERIAL NOT NULL PRIMARY KEY, review VARCHAR);"
]
for sql in sqls:
	try:
		users = db.execute("SELECT * from users;").fetchall()
		db.execute(sql)
	except:
		continue
db.commit()
@app.route("/")
@app.route("/index")
def index():
   s=session["log"]
   return render_template("index.html",users=users,s=s)


#register form
@app.route("/register",methods=["GET","POST"])
def register():
	if request.method=="POST":
		username=request.form.get("username")
		email=request.form.get("email")
		password=request.form.get("password")
		confirm=request.form.get("confirm")
		secure_password=sha256_crypt.encrypt(str(password))

		usernamedata=db.execute("SELECT username FROM users WHERE username=:username",{"username":username}).fetchone()
		#usernamedata=str(usernamedata)
		if usernamedata==None: #check if the username doesnt already exist
			if password==confirm:
				db.execute("INSERT INTO users(email,username,password) VALUES(:email,:username,:password)",
					{"email":email,"username":username,"password":secure_password})
				db.commit()
				flash("You are registered and can now login","success")
				return redirect(url_for('login'))
			else:
				flash("password does not match","danger")
				return render_template('register.html')
		else:
			flash("user already existed, please login ","danger")
			return redirect(url_for('login'))

	return render_template('register.html')
 
@app.route("/login",methods=["GET","POST"])
def login():
	if request.method=="POST":
		username=request.form.get("username")
		password=request.form.get("password")

		usernamedata=db.execute("SELECT username FROM users WHERE username=:username",{"username":username}).fetchone()
		passworddata=db.execute("SELECT password FROM users WHERE username=:username",{"username":username}).fetchone()
 
		if usernamedata is None:
			flash("Invalid credentials","danger")
			return render_template('login.html')
		else:
			for passwor_data in passworddata:
				if sha256_crypt.verify(password,passwor_data):
					session["log"] = True
					flash("You are now logged in!!","success")
					return redirect(url_for('search'))
				else:
					flash("Invalid credentials","danger")
					return render_template('login.html')

	return render_template('login.html')
	
@app.route('/logout')
def logout():
   # remove the username from the session if it is there
   session.pop('username', None)
   session["log"] = False # I use this in the layout to display the right menu
   return redirect(url_for('index'))

# HELPER FUNCTION 
def db_query(query_method,user_query):
	""" this function takes the method of query (by isbn or title or author name)
	search for a match in the database and return a list of all the matches
	"""
	all_results = db.execute("SELECT id, "+query_method+" FROM books").fetchall()
	db_result = {}
	user_query = user_query.lower()
	for query in all_results:
		if user_query in str(query[1]).lower() and user_query != "": # check if the user input is in the result from the database
			id = query[0]
			db_result[id] = query[1] # query is in tuple (id,element)
			
			
	if db_result == []:
		msg = [" There is no " + query_method + " associated with what you requested"]
		return msg
	return db_result # return a dictionary with all the key and values of the querry
query_results = {}
@app.route("/search", methods=["GET","POST"]) #get access only through the form
def search():
	
	if session["log"]: #check if the user is logged in
		if request.method == "POST":
			session["isbn"] = request.form["search_isbn"]
			session["author"] = request.form["search_author"]
			session["title"] = request.form["search_title"]
			# make sure that only one field is used to get the result to make it faster		
			if session["isbn"] != "":
				query_results = db_query("isbn",session["isbn"])
			elif session["author"] != "":
				query_results = db_query("author",session["author"])
			elif session["title"] != "":
				query_results = db_query("title",session["title"]) # each element return a dictionary {id:isbn}
			
			return render_template("search.html",query_results=query_results,show=True)
		return render_template("search.html",show=False)
	else: 
		flash("Please, Login")
		return redirect(url_for('login'))
	

	
@app.route("/bookPage/<string:id>", methods=["GET","POST"])
def bookPage(id):
	#details = []
	#for results in query_results:
	details = db.execute("SELECT isbn, author, title, publication FROM books WHERE id=:id",{"id":id}).fetchone()
	
	return render_template("bookspage.html",id=id, details = details)