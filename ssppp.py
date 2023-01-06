import json
import requests
import time
import math
from os import name
from flask import Flask

class Credentials:
    def __init__(self):
        self.access_token = self.get_credentials()

    # get request for new access token
    def refresh_token(self, r_token):
        # variables for request - url and reading data from json
        url = "https://www.strava.com/oauth/token"
        creds_file = open("useful_files/creds.json", "r")
        creds_data = json.load(creds_file)
        client_id = creds_data["client_id"]
        client_secret = creds_data["secret"]

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
        print(result_json)

        return result_json

    # update file with proper access token if it has expired
    def get_credentials(self):
        # open json file, deserialize
        self.auth_file = open("useful_files/auth.json", "r+")
        self.auth_data = json.load(self.auth_file)

        # if the access token has expired, get a new one using the refresh token.
        current_time = time.time()
        if (self.auth_data["expires_at"] < current_time):
            new_data = self.refresh_token(self.auth_data["refresh_token"])

            # rewrite with new access token
            self.auth_data = new_data
            self.auth_file.seek(0)
            json.dump(self.auth_data, self.auth_file, indent=4)
            self.auth_file.truncate()

        self.auth_file.close()
        return self.auth_data["access_token"]

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
        # not really necessary for now but this writes the segment to a file
        self.seg = open('useful_files/segment.json', "r+")

        self.seg_result = requests.get(segment_url + str(self.id), params=Calculation.payload)
        self.seg_result_json = self.seg_result.json()

        self.seg.seek(0)
        json.dump(self.seg_result_json, self.seg, indent=4)
        self.seg.truncate()

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

        self.seg.close()

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

segment_ids = [30517196]
segment_url = 'https://www.strava.com/api/v3/segments/'

total = 0


for id in segment_ids:
    segment_effort_pp = Calculation(id, 0)
    total += segment_effort_pp.pp
