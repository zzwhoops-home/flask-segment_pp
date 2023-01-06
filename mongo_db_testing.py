from flask import Flask
import pymongo
from pymongo import MongoClient
from urllib import parse
import time

# creating flask app object
app = Flask(__name__)

# mongodb connection configuration and collections
password = parse.quote_plus('')
db_name = parse.quote_plus('')
client = MongoClient(f"mongodb+srv://admin:{password}@ssppp-database.dlpu9.mongodb.net/{db_name}?retryWrites=true&w=majority")
database = client.ssppp_database

access_tokens = database.access_tokens
refresh_tokens = database.refresh_tokens
athlete_info = database.athlete_info

@app.route("/user_profile/<id>")
def user_profile(id):
    print(id)
    # find user access token
    query = {
        'id': int(id)
    }
    for x in access_tokens.find(query):
        print(x)
    return "hi"

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
