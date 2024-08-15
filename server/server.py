import json
import requests
import argparse
import sqlite3
import logging
from flask import current_app, g, Flask, flash, jsonify, redirect, render_template, request, session, Response
import googlemaps
import geopandas as gpd
import pandas as pd
from datetime import datetime
import os
from pathlib import Path

#Other File imports: DB for database interaction, calculations, support.
from db import DB, STATEDICT

## Sets environment variables based on locale
config_check = Path("config.py")
if config_check.is_file():
    ## Environment Variables in for local development
    from config import flask_key, google_key, mapbox_key
else:
    ## Environment Variables for heroku local or production
    flask_key = os.environ.get('flask_key')
    mapbox_key = os.environ.get('mapbox_key')
    google_key = os.environ.get('google_key')

STATES = [ "Alabama","Alaska", "Arizona","Arkansas", "California", "Colorado", 
    "Conneticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", 
    "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", 
    "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", 
    "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", 
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", 
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", 
    "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]

STATELOC = {'Alabama': {'lat': 32.3182314, 'long': -86.902298},
            'Alaska': {'lat': 63.588753, 'long': -154.4930619},
            'Arizona': {'lat': 34.0489281, 'long': -111.0937311},
            'Arkansas': {'lat': 35.20105, 'long': -91.8318334},
            'California': {'lat': 36.778261, 'long': -119.4179324},
            'Colorado': {'lat': 39.5500507, 'long': -105.7820674},
            'Conneticut': {'lat': 41.6032207, 'long': -73.087749},
            'Delaware': {'lat': 38.9108325, 'long': -75.52766989999999},
            'Florida': {'lat': 27.6648274, 'long': -81.5157535},
            'Georgia': {'lat': 32.1574351, 'long': -82.90712300000001},
            'Hawaii': {'lat': 19.8986819, 'long': -155.6658568},
            'Idaho': {'lat': 44.0682019, 'long': -114.7420408},
            'Illinois': {'lat': 40.6331249, 'long': -89.3985283},
            'Indiana': {'lat': 39.76909, 'long': -86.158018},
            'Iowa': {'lat': 41.8780025, 'long': -93.097702},
            'Kansas': {'lat': 39.011902, 'long': -98.4842465},
            'Kentucky': {'lat': 37.8393332, 'long': -84.2700179},
            'Louisiana': {'lat': 30.5190775, 'long': -91.5208624},
            'Maine': {'lat': 45.253783, 'long': -69.4454689},
            'Maryland': {'lat': 39.0457549, 'long': -76.64127119999999},
            'Massachusetts': {'lat': 42.4072107, 'long': -71.3824374},
            'Michigan': {'lat': 44.3148443, 'long': -85.60236429999999},
            'Minnesota': {'lat': 46.729553, 'long': -94.6858998},
            'Mississippi': {'lat': 32.3546679, 'long': -89.3985283},
            'Missouri': {'lat': 37.9642529, 'long': -91.8318334},
            'Montana': {'lat': 46.8796822, 'long': -110.3625658},
            'Nebraska': {'lat': 41.4925374, 'long': -99.9018131},
            'Nevada': {'lat': 38.8026097, 'long': -116.419389},
            'New Hampshire': {'lat': 43.1938516, 'long': -71.5723953},
            'New Jersey': {'lat': 40.0583238, 'long': -74.4056612},
            'New Mexico': {'lat': 34.9727305, 'long': -105.0323635},
            'New York': {'lat': 40.7127753, 'long': -74.0059728},
            'North Carolina': {'lat': 35.7595731, 'long': -79.01929969999999},
            'North Dakota': {'lat': 47.5514926, 'long': -101.0020119},
            'Ohio': {'lat': 40.4172871, 'long': -82.90712300000001},
            'Oklahoma': {'lat': 35.0077519, 'long': -97.092877},
            'Oregon': {'lat': 43.8041334, 'long': -120.5542012},
            'Pennsylvania': {'lat': 41.2033216, 'long': -77.1945247},
            'Rhode Island': {'lat': 41.5800945, 'long': -71.4774291},
            'South Carolina': {'lat': 33.836081, 'long': -81.1637245},
            'South Dakota': {'lat': 43.9695148, 'long': -99.9018131},
            'Tennessee': {'lat': 35.5174913, 'long': -86.5804473},
            'Texas': {'lat': 31.9685988, 'long': -99.9018131},
            'Utah': {'lat': 40.7606608, 'long': -111.8939487},
            'Vermont': {'lat': 44.5588028, 'long': -72.57784149999999},
            'Virginia': {'lat': 37.4315734, 'long': -78.6568942},
            'Washington': {'lat': 47.7510741, 'long': -120.7401386},
            'West Virginia': {'lat': 38.5976262, 'long': -80.4549026},
            'Wisconsin': {'lat': 43.7844397, 'long': -88.7878678},
            'Wyoming': {'lat': 43.0759678, 'long': -107.2902839}}

# base setup
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
# I need to understand this functionality (I currently do not)
# required for consistent session(s)?

app.secret_key = flask_key
gmaps = googlemaps.Client(key=google_key)

# path to db
DATABASE = 'powermax.db'

def get_db_conn():
    """ 
    gets connection to database
    """
    if "_database" not in app.config:
        app.config["_database"] = sqlite3.connect(DATABASE)
        return app.config["_database"] 
    else:
        return app.config["_database"] 

# SITE PAGES AND WIDGETS ------------------------------------------------ 
# Note- can't use logging.info messages here to check things?

def dataloader():
    # Imports shapefiles, elections, and candidates(soonTM) as dataframes and
    # Holds them in memory???
    db = DB()
    elections, allshapes, candidates = db.import_data_v2()
    return elections, allshapes, candidates

with app.app_context():
    logging.info("VM Activated")
    ELECTIONS, ALLSHAPES, CANDIDATES = dataloader()



# Website Home Page 
@app.route('/', methods = ["GET", "POST"])
def home():
    '''
    Renders the homepage.
    '''
    return render_template("home.html", states = STATES, mapbox_key = mapbox_key)

@app.route('/local', methods=["GET", "POST"])
# Geocodes the location of the person and calls the election mapper
def local_elections():
    if request.method == "POST":
        try:
            location = request.form.get("location")
            location =  gmaps.geocode(location)
            return election_delivery_function(location)
        except:
            return redirect('/')
    else:
        return redirect('/')

    
@app.route('/state', methods=["GET", "POST"])
# Passes the state input to and calls the election mapper
def state_elections():
    if request.method == "POST":
        location = request.form.get("location")
        return election_delivery_function(location)
    else:
        return redirect('/')

@app.route('/voter-power', methods=["GET", "POST"])
# It's the vp infographic page.
def vp_load():
    return render_template("vp.html")

@app.route('/about', methods=["GET", "POST"])
# It's the about page.
def about_load():
    return render_template("about.html")

@app.route('/faq', methods=["GET", "POST"])
# It's the FAQ page.
def faq_load():
    return render_template("faq.html")

@app.route('/feedback', methods=["GET", "POST"])
# It's the feedback page.
def feedback_load():
    return render_template("feedback.html")

@app.route('/get-involved', methods=["GET", "POST"])
# Page delivering links to each candidate

def get_involved():
    # Gets the candidates in the election from the state/local page
    if request.method == "POST":
        candidates = request.form.get("candidates")
        candidates = json.loads(candidates)
        #I've set this as a base string for now, can switch to a nicer description later
        election = request.form.get("election")
    else:
        return redirect('/')

    print("Cands", candidates)
    print("elec", type(election), election)
    # Gets the candidate information from the candidate DB
    # Writes a nice HTML string for each candidate
    db = DB()
    db.grab_dataframes(ELECTIONS, ALLSHAPES, CANDIDATES)
    output = db.candidate_link_strings(candidates)
    
    return render_template("getinvolved.html", candidates = output, election = election)

# Utilities ------------------------------

def election_delivery_function(location):
    '''
    Takes a location and returns the elections that are related to those shapes.
    For an exact location, returns elections within ~50 miles.
    For a state, returns elections within that state.
    
    '''
    db = DB()
    db.grab_dataframes(ELECTIONS, ALLSHAPES, CANDIDATES)
        
    # Dictionary to store information from shape lookup
    lookup_dict = {"elections": {},"layers": {}}
    lookup_components = ["Presidential","Senate","House", "Governor", "State Leg (Upper)",
                              "State Leg (Lower)", "Ballot Initiative"]
    ballot_initiative_types = ["Reproductive Rights", "Democracy Repair",
                                "Direct Democracy", "Civil Liberties"]
    
    election_count = 0 # Used for setting up election detail buttons
    # Gets information to place in dictionary
    for i in lookup_components:
        Nelections, shapelayer, election_count = db.nearby_voting_impact(location, i, election_count)
        lookup_dict["elections"][i] = Nelections
        lookup_dict["layers"][i] = shapelayer

    # Some alternative setup for getting split shapelayers per ballot initiative?
    '''
    for j in ballot_initiative_types:
        Nelections, shapelayer = db.nearby_voting_impact(location, i)
        lookup_dict["elections"][i] = Nelections
        lookup_dict["layers"][i] = shapelayer
    '''

    # Get Lat/Long coordinates for centering
    if type(location) != type([]):
        lat = STATELOC[location]["lat"]
        long = STATELOC[location]["long"]
    else:
        lat = location[0]["geometry"]["location"]["lat"]
        long = location[0]["geometry"]["location"]["lng"]

    # All the individual pieces for the detail lookup. May need to add vals
    # for zoom and center for the map as well, depending on address lookup
    return render_template("detail.html", pres_list = lookup_dict["elections"]["Presidential"],
                senate_list = lookup_dict["elections"]["Senate"], 
                house_list = lookup_dict["elections"]["House"], 
                state_house_list = lookup_dict["elections"]["State Leg (Lower)"], 
                state_senate_list = lookup_dict["elections"]["State Leg (Upper)"],
                governor_list = lookup_dict["elections"]["Governor"],
                ballot_list = lookup_dict["elections"]["Ballot Initiative"],
                pres_layer = lookup_dict["layers"]["Presidential"],
                senate_layer = lookup_dict["layers"]["Senate"], 
                house_layer = lookup_dict["layers"]["House"], 
                s_house_layer = lookup_dict["layers"]["State Leg (Lower)"],
                s_sen_layer = lookup_dict["layers"]["State Leg (Upper)"],
                governor_layer = lookup_dict["layers"]["Governor"],
                ballot_layer = lookup_dict["layers"]["Ballot Initiative"],
                lat = lat,
                long = long,
                mapbox_key = mapbox_key)


# Default Hostname/address code for temporary testing purposes
# Logging settings for log debugging
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        help = "Server hostname (default 127.0.0.1)",
        default = "127.0.0.1"
    )
    parser.add_argument(
        "-p", "--port",
        help="Server port (default 5000)",
        default = 5000,
    )
    parser.add_argument(
        "-l", "--log",
        help="Set the log level (debug,info,warning,error)",
        default="warning",
        choices=['debug', 'info', 'warning', 'error']
    )
    parser.add_argument(
        "-d", "--dev",
        help="Configuration host spot options",
        default= 'dev',
        choices=['dev', 'prod']
    )

    # The format for our logger
    log_fmt = '%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s'
    
    # Create the parser argument object
    args = parser.parse_args()
    if args.log == 'debug':
        logging.basicConfig(
            format=log_fmt, level=logging.DEBUG)
        logging.debug("Logging level set to debug")
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.DEBUG)
    elif args.log == 'info':
        logging.basicConfig(
            format=log_fmt, level=logging.INFO)
        logging.info("Logging level set to info")
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.INFO)
    elif args.log == 'warning':
        logging.basicConfig(
            format=log_fmt, level=logging.WARNING)
        logging.warning("Logging level set to warning")
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)
    elif args.log == 'error':
        logging.basicConfig(
            format=log_fmt, level=logging.ERROR)
        logging.error("Logging level set to error")
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
    
    #I really would prefer this be a sysarg but I don't know enough about them to make it work
    if not config_check.is_file():
        print("And I ask myself- well, how did I get here?")
        args.port = int(os.environ.get("PORT",5000))
        args.host = '0.0.0.0'

    # Store the address for the web app
    # app.config['addr'] = "http://%s:%s" % (args.host, args.port)
    print("Port it needs to use: ", int(os.environ.get("PORT",5000)))

    logging.info("Starting Up!")
    print("STARTING with:", args.host, args.port)
    app.run(host=args.host, port=args.port, threaded=False) #pulled out: 
