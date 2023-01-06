from os import sep
import requests
import json

f = open("paces.json", "w")

url = "https://www.strava.com/api/v3/athlete/activities"

payload = {
    'access_token': '',
    'before': 1642136400,
    'page': 1,
    'per_page': 200
}

activities = []

for x in range(2):
    payload['page'] = x + 1
    result = requests.get(url, json=payload)
    activities += result.json()

paces = []

for activity in activities:
    if (activity["type"] != "Run"): continue
    avg_speed = (1 / activity["average_speed"]) * 26.8166667
    separate = str(avg_speed).split(".")
    min = separate[0]
    sec = str(round(float(f".{separate[1]}") * 60))
    if (len(sec) == 1):
        sec = f"0{sec}"
    if (sec == "60"):
        sec = "00"
        min = str(int(min) + 1)

    text = f"{min}:{sec}"
    paces.append(text)

paces.sort()

graph_vals = {}
for pace in paces:
    if pace not in graph_vals.keys():
        graph_vals[pace] = 1
    else:
        graph_vals[pace] += 1

json.dump(graph_vals, f, indent=4)

f.close()