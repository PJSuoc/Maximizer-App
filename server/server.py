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

#Other File imports: DB for database interaction, calculations, support.
from db import DB, STATEDICT
from config import flask_key, google_key, mapbox_key

STATES = [ "Alabama","Alaska", "Arizona","Arkansas", "California", "Colorado", 
    "Conneticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", 
    "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", 
    "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", 
    "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", 
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", 
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", 
    "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]


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
    db = DB(get_db_conn())
    elections, allshapes, candidates = db.import_data_v2()
    db.conn.close()
    return elections, allshapes, candidates

with app.app_context():
    ELECTIONS, ALLSHAPES, CANDIDATES = dataloader()



# Website Home Page 
@app.route('/', methods = ["GET", "POST"])
def home():
    '''
    Renders the homepage.
    '''
    print("Anybody home?")
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
            #flash('Unable to locate address', 'error') Doesn't work smh
            return redirect('/')

    
@app.route('/state', methods=["GET", "POST"])
# Passes the state input to and calls the election mapper
def state_elections():
    if request.method == "POST":
        location = request.form.get("location")
        return election_delivery_function(location)

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

@app.route('/get-involved', methods=["GET", "POST"])
# Page delivering links to each candidate
def get_involved():
    # Gets the candidates in the election from the state/local page
    if request.method == "POST":
        print(request.form.get("candidates"), type(request.form.get("candidates")))
        candidates = request.form.get("candidates")
        candidates = json.loads(candidates)
    else:
        candidates = []

    print(candidates, type(candidates))
    # Gets the candidate information from the candidate DB
    # Writes a nice HTML string for each candidate
    db = DB(get_db_conn())
    db.grab_dataframes(ELECTIONS, ALLSHAPES, CANDIDATES)
    output = db.candidate_link_strings(candidates)
    db.conn.close()
    
    return render_template("getinvolved.html", candidates = output)

# Utilities ------------------------------

def election_delivery_function(location):
    '''
    Takes a location and returns the elections that are related to those shapes.
    For an exact location, returns elections within ~50 miles.
    For a state, returns elections within that state.
    
    '''
    db = DB(get_db_conn())
    db.grab_dataframes(ELECTIONS, ALLSHAPES, CANDIDATES)
        
    # Dictionary to store information from shape lookup
    lookup_dict = {"elections": {},"layers": {}}
    lookup_components = ["Presidential","Senate","House", "State Leg (Upper)",
                              "State Leg (Lower)", "Ballot Initiative"]
    ballot_initiative_types = ["Reproductive Rights", "Democracy Repair",
                                "Direct Democracy", "Whatever else"]
    # Gets information to place in dictionary
    election_count = 0
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
        location =  gmaps.geocode(location)
    lat = location[0]["geometry"]["location"]["lat"]
    long = location[0]["geometry"]["location"]["lng"]

    db.conn.close()
    # All the individual pieces for the detail lookup. May need to add vals
    # for zoom and center for the map as well, depending on address lookup
    return render_template("detail.html", pres_list = lookup_dict["elections"]["Presidential"],
                senate_list = lookup_dict["elections"]["Senate"], 
                house_list = lookup_dict["elections"]["House"], 
                state_house_list = lookup_dict["elections"]["State Leg (Lower)"], 
                state_senate_list = lookup_dict["elections"]["State Leg (Upper)"],
                #governor_list = lookup_dict["elections"]["Governor"],
                ballot_list = lookup_dict["elections"]["Ballot Initiative"],
                pres_layer = lookup_dict["layers"]["Presidential"],
                senate_layer = lookup_dict["layers"]["Senate"], 
                house_layer = lookup_dict["layers"]["House"], 
                s_house_layer = lookup_dict["layers"]["State Leg (Lower)"],
                s_sen_layer = lookup_dict["layers"]["State Leg (Upper)"],
                #governor_layer = lookup_dict["layers"]["Governor"],
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
        help="Server hostname (default 127.0.0.1)",
        default="127.0.0.1"
    )
    parser.add_argument(
        "-p", "--port",
        help="Server port (default 5000)",
        default=5000,
        type=int
    )
    parser.add_argument(
        "-l", "--log",
        help="Set the log level (debug,info,warning,error)",
        default="warning",
        choices=['debug', 'info', 'warning', 'error']
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

    # Store the address for the web app
    app.config['addr'] = "http://%s:%s" % (args.host, args.port)

    logging.info("Starting Up!")
    app.run(host=args.host, port=args.port, threaded=False)
