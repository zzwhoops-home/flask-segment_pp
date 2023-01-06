from os import access
from flask import Flask, request, jsonify, redirect, Response, url_for, render_template
from flask.templating import render_template
from markupsafe import escape
import requests
from pymongo import MongoClient
from urllib import parse
import urllib
import time
import math
import re

# mongodb connection configuration and collections
password = parse.quote_plus('')
db_name = parse.quote_plus('')
client = MongoClient(f"mongodb+srv://admin:{password}@ssppp-database.dlpu9.mongodb.net/{db_name}?retryWrites=true&w=majority")
database = client.ssppp_database

access_tokens = database.access_tokens
refresh_tokens = database.refresh_tokens
athlete_info = database.athlete_info
segment_info = database.segment_info

# creating flask app object
app = Flask(__name__)
client_id = 74853
client_secret = ''

# urls
segment_url = 'https://www.strava.com/api/v3/segments'

# segments to calculate pp for
segments = [30517196, 7005840, 7257213, 18169104, 4113975, 15354473, 12520784, 7481358, 24014015]

@app.route("/")
def index():
    return render_template('home.html')

@app.route("/info")
def info():
    return render_template('info.html')

@app.route("/updates")
def updates():
    return render_template("updates.html")

# after user clicks on strava login button, redirects to page where user authorizes application, which redirects back to website to exchange token 
@app.route("/strava_login", methods=['GET'])
def strava_login():
    payload = {
        'client_id': client_id,
        'redirect_uri': 'http://127.0.0.1:8080/strava_token',
        'response_type': 'code',
        'approval_prompt': 'auto',
        'scope': 'activity:read_all,profile:write'
    }
    url="{}?{}".format('https://www.strava.com/oauth/authorize', urllib.parse.urlencode(payload))
    return redirect(url)

# exchange token
def token_exchange(code):
    url = 'https://www.strava.com/oauth/token'

    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code'
    }

    result = requests.post(url, data=payload).json()
    return result

# get data required for calculation
@app.route("/strava_token", methods=['GET'])
def strava_token():
    code = request.args.get('code', '')
    error = request.args.get('error', '')
    scopes = request.args.get('scope', '')
    if error:
        return Response('Error: User canceled authorization. Access denied.', status=403)
    if not code:
        return Response('Error: Bad request. Try again later.', status=400)
    if 'read,activity:read_all' not in scopes:
        return Response('Error: You must check all boxes for Segment PP to work. Please try again. You will be redirected back in 3 seconds.'), {"Refresh": "3; url=/strava_login"}

    result = token_exchange(code)
    update_athlete_info(result, scopes)
    return redirect(url_for('.user_profile', id=result['athlete']['id']))

# post request for new access token
def update_tokens(r_token):
    url = "https://www.strava.com/api/v3/oauth/token"

    # request headers
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': r_token,
        'grant_type': 'refresh_token'
    }
    # get json request and return it
    result = requests.post(url, data=payload)
    result_json = result.json()
    return result_json

@app.route("/user_profile/<id>")
def user_profile(id):

    id = int(id)
    # find user access token
    query = {
        'id': id
    }
    access_token_data = access_tokens.find_one(query)
    access_token = access_token_data['access_token']
    expires_at = access_token_data['expires_at']
    current_time = time.time()
    
    # if the access token has expired, get a new one using the refresh token.
    if (expires_at <= current_time):
        # find refresh token for user id
        refresh_token = refresh_tokens.find_one(query)['refresh_token']
        result = update_tokens(refresh_token)

        # write new access token, expiration date, and refresh token to their respective tables
        access_token = result['access_token']
        refresh_token = result['refresh_token']
        expires_at = result['expires_at']

        modify_access_entry(id, access_token, expires_at)
        modify_refresh_entry(id, refresh_token)

    # starring segments to get all of them in one request
    star_segments(segments, access_token)

    athlete_query = athlete_info.find_one(query)
    name = athlete_query['first_name'] + ' ' + athlete_query['last_name']
    sex = athlete_query['sex']
    # the starred segments not including total elevation gain causes us to write 20 extra lines of code and destroy efficiency
    payload = {
        'access_token': access_token
    }
    url = f'{segment_url}/starred'
    segment_starred_data = requests.get(url, json=payload).json()
    segment_prs = {}
    for segment in segment_starred_data:
        # ensure that the athlete has an effort on the segment and that the segment is in the list of ranked segments.
        if ('pr_time' in segment) and (segment['id'] in segments):
            segment_prs[segment['id']] = segment['pr_time']
    segment_ids = list(segment_prs.keys())
    calculation = Calculation(segment_prs, segment_ids, sex)
    segment_pps = calculation.segment_pps
    
    sorted_segment_pps = dict(sorted(segment_pps.items(), key=lambda item: item[1]['total_pp'], reverse=True))
    sorted_segment_ids = sorted_segment_pps.keys()

    print (segment_pps)
    print("\n\n\n\n")
    print (sorted_segment_pps)

    total_pp = round(calculation.pp, 2)

    avatar_link = athlete_info.find_one(query)['avatar_link']

    return render_template('results.html', user_name = name, avatar = avatar_link, total_pp = total_pp, segment_ids = sorted_segment_ids, display_vals = sorted_segment_pps)
    #return render_template('results.html', user_name = (first_name + ' ' + last_name))

# access tokens: check if athlete id already exists, create new entry if not, update entry if yes 
def modify_access_entry(id, access_token, current_time=0, expires_at=0, correct_scope=True):
    id = int(id)
    access_exists = access_tokens.find_one({"id": id})
    if access_exists != None:
        query = {
            'id': id
        }
        data = {
            "$set":
            {
                'access_token': access_token,
                'expires_at': expires_at,
                'scope': correct_scope
            }
        }
        access_tokens.update_one(query, data)
    else:
        data = {
            'id': id,
            'access_token': access_token,
            'epoch_join': current_time,
            'expires_at': expires_at,
            'scope': correct_scope
        }
        access_tokens.insert_one(data)

# same thing as above but with refresh tokens
def modify_refresh_entry(id, refresh_token, current_time=0, correct_scope=True):
    id = int(id)
    refresh_exists = refresh_tokens.find_one({"id": id})
    if refresh_exists != None:
        query = {
            'id': id
        }
        data = {
            "$set":
            {
                'refresh_token': refresh_token,
                'scope': correct_scope
            }
        }
        refresh_tokens.update_one(query, data)
    else:
        data = {
            'id': id,
            'refresh_token': refresh_token,
            'epoch_join': current_time,
            'scope': correct_scope
        }
        refresh_tokens.insert_one(data)

# same thing as above but with athlete information
def modify_athlete_entry(id, username="", first_name="", last_name="", city="", state="", country="", sex="", avatar="", current_time=0):
    id = int(id)
    athlete_exists = athlete_info.find_one({"id": id})
    if athlete_exists != None:
        query = {
            'id': id
        }
        data = {
            "$set":
            {
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'city': city,
                'state': state,
                'country': country,
                'sex': sex,
                'avatar_link': avatar
            }
        }
        athlete_info.update_one(query, data)
    else:
        data = {
            'id': id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'city': city,
            'state': state,
            'country': country,
            'sex': sex,
            'avatar_link': avatar,
            'epoch_join': current_time
        }
        athlete_info.insert_one(data)

def update_athlete_info(result, scopes):
    # variables from authentication returned result
    athlete = result['athlete']
    id = int(athlete['id'])
    username = athlete['username']
    first_name = athlete['firstname']
    last_name = athlete['lastname']
    city = athlete['city']
    state = athlete['state']
    country = athlete['country']
    sex = athlete['sex']
    avatar = athlete['profile_medium']

    correct_scope = True if scopes == 'read,activity:read_all,profile:write' else False    
    access_token = result['access_token']
    refresh_token = result['refresh_token']
    expires_at = result['expires_at']
    current_time = time.time()

    # call function to change or add athlete access token entry
    modify_access_entry(id, access_token, current_time, expires_at=expires_at, correct_scope=correct_scope)

    # same as above, with refresh token entry
    modify_refresh_entry(id, refresh_token, current_time, correct_scope=correct_scope)
    
    # same as above, but with an athlete information entry
    modify_athlete_entry(id, username, first_name, last_name, city, state, country, sex, avatar, current_time)

def star_segments(segment_ids, access_token):
    # get a list of user's current starred segments
    payload = {
        'access_token': access_token
    }
    starred_result = requests.get(f'{segment_url}/starred', params=payload)
    starred_result_json = starred_result.json()
    cur_starred = []
    for segment in starred_result_json:
        cur_starred.append(segment['id'])

    # star each segment if the athlete has not starred them already (to help with api rate limit)
    not_starred = list(set(segment_ids).difference(cur_starred))

    star_payload = {
        'access_token': access_token,
        'starred': 'true'
    }
    for segment_id in not_starred:
        url = f"{segment_url}/{segment_id}/starred"
        requests.put(url, json=star_payload)

class Calculation:
    # weights for each pp component
    dist_weight = 0.3
    spd_weight = 0.3
    ter_weight = 0.15
    comp_weight = 0.25

    def __init__(self, segment_prs, segment_ids, sex):
        self.segment_prs = segment_prs
        self.segment_ids = segment_ids
        self.sex = sex
        self.pp = 0
        self.segment_pps = {}

        for segment_id in segment_ids:
            query = {
                'id': segment_id
            }
            segment_data = segment_info.find_one(query)
            segment_pr = segment_prs[segment_id]
            self.segment_pps[segment_id] = self.get_segment(segment_pr, segment_data)

    # get segment and calculate its pp value for the authenticated athlete
    def get_segment(self, pr, data):
        pp = 0
        seg_pr = pr
        dist = data['distance']
        # different CR depending on sex
        if (self.sex == 'M'):
            seg_cr = self.cr_string_sec(data['xoms']['kom'])
        elif (self.sex == 'F'):
            seg_cr = self.cr_string_sec(data['xoms']['qom'])
        atts = data['effort_count']
        ppl = data['athlete_count']
        elev_gain = data['total_elevation_gain']
        avg_grade = data['average_grade'] / 100
        max_grade = data['maximum_grade'] / 100
        pace = seg_pr / (dist * 0.000621371192)
        name = data['name']

        dist_pp = self.dist_pp(dist)
        spd_pp = self.spd_pp(pace)
        terr_pp = self.terr_pp(avg_grade, max_grade, elev_gain, dist)
        comp_pp = self.comp_pp(seg_pr, seg_cr, atts, ppl)
        pp += dist_pp + spd_pp + terr_pp + comp_pp

        segment_vals = {
            'name': name,
            'dist': dist,
            'pace': round(pace, 2),
            # 'pace_adj': pace_adj,
            'seg_pr': seg_pr,
            'seg_cr': seg_cr,
            'attempts': atts,
            'athletes': ppl,
            'elev_gain': elev_gain,
            'avg_grade': avg_grade,
            'max_grade': max_grade,
            'dist_pp': round(dist_pp, 2),
            'spd_pp': round(spd_pp, 2),
            'terr_pp': round(terr_pp, 2),
            'comp_pp': round(comp_pp, 2),
            'total_pp': round(pp, 2)
        }
        self.pp += pp
        return segment_vals

    def cr_string_sec(self, string_cr):
        pattern = '^[0-9:]*'
        multis = [1, 60, 3600]
        time = (re.match(pattern, string_cr).group(0)).split(':')
        seg_cr = 0
        for x in range(len(time)):
            seg_cr += int(time[x]) * multis[len(time)- 1 - x]
        return seg_cr

    def dist_pp(self, dist):
        return (4.2 * (dist ** 0.4) - 21) * Calculation.dist_weight

    def spd_pp(self, pace):
        # change program to have pace in min/mi so the pace / 60 to go from sec/mi to min/mi conversion is not necessary
        pace = pace / 60
        if (pace > 3.186):
            base = ((-math.log(pace - 2) / 0.9) + 1.85) * 169 * Calculation.spd_weight
        else:
            base = (-(pow(pace, 0.4)) + 3.25) * 169 * Calculation.spd_weight
            
        return max(0, base)

    def terr_pp(self, avg_grade, max_grade, elev_gain, dist):
        terr_pp = abs((avg_grade * 0.7 + max_grade * 0.3) * Calculation.spd_weight * 2000) ** 1.2
        return max(0, terr_pp)

    def comp_pp(self, seg_pr, seg_cr, atts, ppl):
        factor = (ppl / atts) ** 0.42
        multiplier = (((math.log(atts) ** 2) / 5) * (25 * (seg_cr / seg_pr) ** 6.9))
        bonus = 0

        if (seg_pr == seg_cr):
            bonus = 30

        return (factor * multiplier + bonus) * Calculation.comp_weight

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)