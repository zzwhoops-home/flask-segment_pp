import requests
from pymongo import MongoClient
from urllib import parse
# mongodb connection configuration and collections
password = parse.quote_plus('')
db_name = parse.quote_plus('')
client = MongoClient(f"mongodb+srv://admin:{password}@ssppp-database.dlpu9.mongodb.net/{db_name}?retryWrites=true&w=majority")
database = client.ssppp_database

segment_info = database.segment_info
segments = [30517196, 7005840, 7257213, 18169104, 4113975, 15354473, 12520784, 7481358, 7481353, 17332283, 9344095, 7443925, 29660648, 11907416, 24014015]

url = 'https://www.strava.com/api/v3/segments'
payload = 
    'access_token': ''
}

existing_segments = segment_info.find({}, { "id": 1 })
existing_segments_list = []
for segment in existing_segments:
    try:
        existing_segments_list.append(segment['id'])
    except KeyError:
        print("refresh access token")
        continue

missing_segments = list(set(segments).difference(existing_segments_list))
print(missing_segments)

action = input("(y) to completely rewrite all segments with fresh data. Anything else = no: ")

if action.lower() == "y":
    for id in segments:
        segment_url = f"{url}/{id}"
        result = requests.get(segment_url, json=payload).json()
        segment_info.insert_one(result)
else:
    for id in missing_segments:
        segment_url = f"{url}/{id}"
        result = requests.get(segment_url, json=payload).json()
        segment_info.insert_one(result)