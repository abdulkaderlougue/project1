import os
import requests
from flask import Flask, session, render_template, request, flash, url_for, redirect, jsonify
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
"CREATE TABLE reviews(id SERIAL NOT NULL PRIMARY KEY, book_id INTEGER REFERENCES books, user_id INTEGER REFERENCES users,rating INTEGER, review VARCHAR);"
]
#db.execute("CREATE TABLE reviews(id SERIAL NOT NULL PRIMARY KEY, book_id INTEGER REFERENCES books, user_id INTEGER REFERENCES users,rating INTEGER, review VARCHAR);")

#This for does not create tables, I dont know why but when I create manually, it works like line 30 above.
for i in range(len(sqls)):
	try:
		db.execute(sqls[i])
	except:
		pass # meaning the table already exists

#db.execute("INSERT INTO reviews(user_id,rating) VALUES(:user_id,:rating)",{"user_id":12,"rating":9})
db.commit()
users = db.execute("SELECT * from users;").fetchall()
reviews = db.execute("SELECT * from reviews;").fetchall()

@app.route("/")
@app.route("/index")
def index():
	if session.get("log") == None:
		session["log"] = False
	s=session["log"]
	return render_template("index.html")


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
		session['username'] = request.form["username"] # will use it to get access to the current user in bookPage

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
		flash("Not Allowed!!! Please, Login")
		return redirect(url_for('login'))
	

	
@app.route("/bookPage/<string:id>", methods=['GET','POST'])
def bookPage(id):
	#details = []
	#for results in query_results:
	#making sure that the user is login before accessing the book details
	if session["log"] == True:
		details = db.execute("SELECT isbn, author, title, publication FROM books WHERE id=:id",{"id":id}).fetchone()
		reviews = db.execute("SELECT review FROM reviews WHERE book_id=:id",{"id":id}).fetchall()
		#ratings = db.execute("SELECT rating FROM reviews WHERE book_id=:id",{"id":id}).fetchall()
		current_user = session['username'] 
		user_id = db.execute("SELECT id FROM users WHERE username=:current_user",{"current_user":current_user}).fetchone()[0] 
		isbn = details[0]
		# API REQUEST FROM GOODREADS
		KEY = "o2yOgTDO1j7THwySt9qU8Q"
		res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": KEY, "isbns": isbn})
		data = res.json()
		avg_rating = data['books'][0]["average_rating"]
		nber_of_rating = data['books'][0]["work_ratings_count"]
		details = list(details)
		details.append(avg_rating)
		details.append(nber_of_rating)
		if alreadyReview(user_id,id) == False:
			review("review","ratingVal",id,user_id)
			showReviewForms = True # show the review space to the user if not reviewed yet hide otherwise
		else:
			showReviewForms = False

		return render_template("bookspage.html",id=id, details = details,reviews=reviews,showReviewForms=showReviewForms)
	else:
		flash("Not Allowed!!! Please, Login")
		return redirect(url_for('login'))

def rate(formName,bookId,userId):
	user_rating = "Rate this book"
	if request.method=="POST":
		user_rating = request.form.get(formName)
		#isReviewed = db.execute("SELECT review FROM reviews WHERE book_id=:bookId AND user_id=:userId",{"bookId":bookId,"userId":userId}).fetchone()
		print(user_rating)
		if user_rating != '': # rating should be an integer
			user_rating = int(user_rating)
			db.execute("INSERT INTO reviews(book_id,user_id,rating) VALUES(:bookId,:userId,:user_rating)",{"bookId":bookId,"userId":userId,"user_rating":user_rating})
			db.commit()
		flash("Thank you for Your review",'success')
	return user_rating

def review(reviewName,ratingName,bookId,userId):
	user_review = "Write a rating for this book"
	user_rating = "Rate this book"
	if request.method=="POST":
		user_review=request.form.get(reviewName) 
		user_rating = request.form.get(ratingName)
		if user_rating != '': # rating should be an integer
			user_rating = int(user_rating)
		db.execute("INSERT INTO reviews(book_id,user_id,rating,review) VALUES(:bookId,:userId,:user_rating,:user_review)",{"bookId":bookId,"userId":userId,"userId":userId,"user_rating":user_rating,"user_review":user_review})
		db.commit()
		flash("Thank you for Your review")
	return [user_rating,user_review] # return the rating value and the review

def alreadyReview(userId,bookId):
#TODO: BAD CODE, SHOULD COME BACK TO IT
	#check if the user already reviewed the book or not	
	#return TRUE if reviwed FALSE otherwise
	review = db.execute("SELECT review FROM reviews WHERE book_id=:bookId AND user_id=:userId",{"bookId":bookId,"userId":userId}).fetchone()
	rating = db.execute("SELECT review FROM reviews WHERE book_id=:bookId AND user_id=:userId",{"bookId":bookId,"userId":userId}).fetchone()
	isReviewed = False
	isRated = False
	if review != None or rating !=  None:
		isReviewed = True
	return isReviewed

@app.route("/api/<string:isbn>")
def api(isbn):

	details = db.execute("SELECT isbn, author, title, publication, id FROM books WHERE isbn=:isbn",{"isbn":isbn}).fetchone()
	if details is None:
		return jsonify({"error": "Invalid ISBN"}),404
	bookId = details[4]
	review_count = 0
	rating_count = 0
	rating_value = 0
	all_reviews_and_ratings = 	db.execute("SELECT review, rating FROM reviews WHERE book_id=:bookId",{"bookId":bookId}).fetchall()

	for review in all_reviews_and_ratings:
		rev = review[0] #review
		rat = review[1] # rating
		
		# this is put in case the user just rate and doesnt review or vise versa
		if rev != None: #check if there is a review written
			review_count += 1
			
		if rat != None: #check if there is a rating
			rating_count += 1
			rating_value += rat
	if rating_count != 0:
		avg_rating = rating_value/rating_count
	else: 
		avg_rating = 'No rating'
	return jsonify({
	"title": details[2],
    "author": details[1],
    "year": details[3],
    "isbn": details[0],
    "review_count": review_count,
    "average_score": avg_rating,
	})

@app.route('/api')
def apiPage():
	return render_template("api.html")