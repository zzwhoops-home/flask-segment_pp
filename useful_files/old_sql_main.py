from flask import Flask, request, jsonify, redirect, Response, url_for
from flask.templating import render_template
import requests
import mysql.connector
from mysql.connector.constants import ClientFlag
import urllib
import time
import math

# configuration for sql database connection
config = {
}
config['database'] = 'segment_pp_database'  # add new database to config dict

# creating flask app object
app = Flask(__name__)
client_id = 74853
client_secret = ''

# urls
segment_url = 'https://www.strava.com/api/v3/segments'

# segments to calculate pp for
segments = [30517196]

@app.route("/")
def index():
    return render_template('home.html')

@app.route("/info")
def info():
    return render_template('info.html')

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
def update_tokens(id, r_token):
    # establishing connection
    sql_connection = mysql.connector.connect(**config)
    cursor = sql_connection.cursor(dictionary=True)

    cursor.execute("SELECT r_token FROM refresh_tokens WHERE id = %s", (id,))
    r_token = cursor.fetchall()[0]['r_token']

    url = "https://www.strava.com/api/v3/oauth/token"

    # request headers
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': r_token,
        'grant_type': 'refresh_token'
    }

    # get json request
    result = requests.post(url, data=payload)
    result_json = result.json()

    cursor.close()
    sql_connection.close()

    return result_json

@app.route("/user_profile/<id>")
def user_profile(id):
    # establishing connection and creating cursor object
    sql_connection = mysql.connector.connect(**config)
    cursor = sql_connection.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM access_tokens WHERE id = %s", (id,))
    a_token_data = cursor.fetchall()[0]
    a_token = a_token_data['a_token']
    expires_at = a_token_data['expires_at']
    current_time = time.time()

    
    # if the access token has expired, get a new one using the refresh token.
    if (expires_at <= current_time):
        # find refresh token for user id
        cursor.execute("SELECT r_token FROM refresh_tokens WHERE id = %s", (id,))
        r_token = cursor.fetchall()[0]
        result = update_tokens(id, r_token)

        # write new access token, expiration date, and refresh token to their respective tables
        access_query = "UPDATE access_tokens SET a_token = %s, expires_at = %s WHERE id = %s"
        access_values = (result['access_token'], result['expires_at'], id)
        cursor.execute(access_query, access_values)

        refresh_query = "UPDATE refresh_tokens SET r_token = %s WHERE id = %s"
        refresh_values = (result['refresh_token'], id)
        cursor.execute(refresh_query, refresh_values)
        
        a_token = result['access_token']

        sql_connection.commit()

    cursor.close()
    sql_connection.close()

    performances = []
    
    star_segments(segments)
    return render_template('results.html', user_name = id)
    #return render_template('results.html', user_name = (first_name + ' ' + last_name))

def update_athlete_info(result, scopes):
    # establishing connection and creating cursor object
    sql_connection = mysql.connector.connect(**config)
    cursor = sql_connection.cursor()

    # variables from authentication returned result
    athlete = result['athlete']
    id = athlete['id']
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

    # access tokens: check if athlete id already exists, create new entry if not, update entry if yes 
    cursor.execute("SELECT EXISTS(SELECT * FROM access_tokens WHERE id=%s)", (id,))
    access_exists = cursor.fetchall()
    
    if '1' in str(access_exists):
        access_query = "UPDATE access_tokens SET scope = %s, a_token = %s, expires_at = %s WHERE id = %s"
        access_values = (correct_scope, access_token, expires_at, id)
    else:
        access_query = "INSERT INTO access_tokens (id, scope, a_token, expires_at, epoch_join) VALUES (%s, %s, %s, %s, %s)"
        access_values = (id, correct_scope, access_token, expires_at, current_time)
    cursor.execute(access_query, access_values)

    # refresh tokens: see above - same thing 
    cursor.execute("SELECT EXISTS(SELECT * FROM refresh_tokens WHERE id=%s)", (id,))
    refresh_exists = cursor.fetchall()
    
    if '1' in str(refresh_exists):
        refresh_query = "UPDATE refresh_tokens SET r_token = %s, scope = %s WHERE id = %s"
        refresh_values = (refresh_token, correct_scope, id)
    else:
        refresh_query = "INSERT INTO refresh_tokens (id, r_token, scope, epoch_join) VALUES (%s, %s, %s, %s)"
        refresh_values = (id, refresh_token, correct_scope, current_time)
    cursor.execute(refresh_query, refresh_values)

    # athlete info, same as above
    cursor.execute("SELECT EXISTS(SELECT * FROM athlete_info WHERE id=%s)", (id,))
    athlete_exists = cursor.fetchall()
    
    if '1' in str(athlete_exists):
        athlete_query = "UPDATE athlete_info SET username = %s, firstname = %s, city = %s, state = %s, country = %s, sex = %s, avatar = %s WHERE id = %s"
        athlete_values = (username, first_name, last_name, city, state, country, sex, avatar)
    else:
        athlete_query = "INSERT INTO athlete_info (id, username, firstname, lastname, city, state, country, sex, avatar, epoch_join) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        athlete_values = (id, username, first_name, last_name, city, state, country, sex, avatar, current_time)
    cursor.execute(athlete_query, athlete_values)

    sql_connection.commit()
    sql_connection.close()

def star_segments(segment_ids):
    # get a list of user's current starred segments
    payload = {
        'access_token': '1d696316df9e907c1ed9c1c8211684a2339e920d'
    }
    starred_result = requests.get(f'{segment_url}/starred', params=payload)
    starred_result_json = starred_result.json()
    cur_starred = []
    for segment in starred_result_json:
        cur_starred.append(segment['id'])

    payload = {
        'access_token': '1d696316df9e907c1ed9c1c8211684a2339e920d',
        'starred': 'true'
    }
    for id in segment_ids:
        url = f"{segment_url}/{id}/starred"
        requests.put(url, json=payload)

"""
class Calculation:
    def __init__(self, id, pp):
        self.id = id
        self.pp = pp
        self.get_segment()

    credentials = Credentials()
    payload = {
        'access_token': credentials.access_token
    }

    # weights for each pp component
    dist_weight = 0.325
    spd_weight = 0.325
    comp_weight = 0.25

    # get segment and calculate its pp value for the authenticated athlete
    def get_segment(self):
        self.seg_result = requests.get(f"{segment_url}/{str(self.id)})", params=Calculation.payload)
        self.seg_result_json = self.seg_result.json()

        loaded = self.seg_result_json
        dist = loaded["distance"]
        seg_pr = loaded["athlete_segment_stats"]["pr_elapsed_time"]
        # if the athlete has never run the segment, there will be no pr, so we return 0 as the pp value
        if (seg_pr is None):
            return 0
        # remember to get female CR if the athlete is female
        seg_cr = loaded["xoms"]["kom"]
        atts = loaded["effort_count"]
        ppl = loaded["athlete_count"]

        time = seg_cr.split(":")
        seg_cr = (float(time[0]) * 60) + float(time[1])

        self.pp += self.dist_pp(dist) + self.spd_pp(seg_pr, dist) + self.comp_pp(seg_pr, seg_cr, atts, ppl)

    def dist_pp(self, dist):
        return (5 * max((8 * math.log(float(dist)) - 37), -2)) * Calculation.dist_weight

    def spd_pp(self, seg_pr, dist):
        pace = (seg_pr / 60) / (dist * 0.000621371192)
        #spd = spd_adj()
        if (pace > 3.665):
            return (-math.log(pace - 2) + 2) * 169 * Calculation.spd_weight
        else:
            return (-(pow(pace, 0.4)) + 3.25) * 169 * Calculation.spd_weight

    def spd_adj(self, dist, elev, pace):
        pass

    def comp_pp(self, seg_pr, seg_cr, atts, ppl):
        factor = (ppl / atts) ** 0.5
        multiplier = (((math.log(atts) ** 2) / 5) * (25 * (seg_cr / seg_pr) ** 6.9))
        bonus = 0

        if (seg_pr == seg_cr):
            bonus = 30

        return (factor * multiplier + bonus) * Calculation.comp_weight
"""
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)