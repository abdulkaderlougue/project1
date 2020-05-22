""" 
Read books data from a csv file csv and create tables in a database and store the data there
"""

import os
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker



# Set up database
engine = create_engine(os.getenv("DATABASE_URL")) #manage connection 
db = scoped_session(sessionmaker(bind=engine))

f = open("books.csv")

reader = csv.reader(f)

book = db.execute("CREATE TABLE books(id SERIAL PRIMARY KEY, isbn VARCHAR UNIQUE NOT NULL, title VARCHAR NOT NULL, author VARCHAR NOT NULL, publication INTEGER NOT NULL,review_count INTEGER , average_score INTEGER);")

count = 0
for isbn, title, author, publication in reader:
	if count != 0: # ignore the first row because it is the field names
		db.execute("INSERT INTO books (isbn, title, author, publication) VALUES (:isbn, :title, :author, :publication)",{"isbn":isbn, "title":title, "author":author, "publication":int(publication)})
	count += 1
db.commit()






