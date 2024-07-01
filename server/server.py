import json
import requests
import argparse
import sqlite3
import logging
from flask import current_app, g, Flask, flash, jsonify, redirect, render_template, request, session, Response
import googlemaps
import geopandas as gpd
#import pandas as pd
from datetime import datetime

#Other File imports: DB for database interaction, calculations, support.
from db import DB
from config import flask_key, google_key, mapbox_key


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

# Website Home Page 
@app.route('/', methods = ["GET", "POST"])
def home():
    '''
    Renders the homepage and contains the code references for detailed
    location lookups.
    '''
    #Address/Location Form Output:
    if request.method == "POST":
        location = request.form.get("location")
        location =  gmaps.geocode(location)
        db = DB(get_db_conn())
        db.import_data()
        
        # Dictionary to store information from shape lookup
        lookup_dict = {"elections": {},"layers": {}}
        lookup_components = ["President","Senate","House", "State Leg (Upper)",
                              "State Leg (Lower)", "Ballot Initiative"]
        
        # Gets information to place in dictionary
        for i in lookup_components:
            elections, shapelayer = db.nearby_voting_impact(location, i)
            lookup_dict["elections"][i] = elections
            lookup_dict["layers"][i] = shapelayer
        
        #senate, senate_layer = db.nearby_voting_impact(location, "states")
        #logging.info(senate)
        #house, house_layer = db.nearby_voting_impact(location, "house")
        #logging.info(house)
        #state_house, s_house_layer = db.nearby_voting_impact(location, "state_house")
        #state_senate, s_sen_layer = db.nearby_voting_impact(location, "state_senate")
        #ballot,_ = db.nearby_voting_impact(location, "ballot")
        #presidential_vp = 20
        db.conn.close()
        return render_template("detail.html", pres_list = lookup_dict["elections"]["President"],
                    senate_list = lookup_dict["elections"]["Senate"], 
                    house_list = lookup_dict["elections"]["House"], 
                    state_house_list = lookup_dict["elections"]["State Leg (Lower)"], 
                    state_senate_list = lookup_dict["elections"]["State Leg (Upper)"],
                    ballot_list = lookup_dict["elections"]["Ballot Initiative"],
                    pres_layer = lookup_dict["layers"]["President"],
                    senate_layer = lookup_dict["layers"]["Senate"], 
                    house_layer = lookup_dict["layers"]["House"], 
                    s_house_layer = lookup_dict["layers"]["State Leg (Lower)"],
                    s_sen_layer = lookup_dict["layers"]["State Leg (Upper)"],
                    ballot_layer = lookup_dict["layers"]["Ballot Initiative"],
                    mapbox_key = mapbox_key)

    #Base Homepage
    return render_template("home.html", mapbox_key = mapbox_key)

def geolocate(): # currently nonfunctional
    location = request.form.get("location")
    geoloc =  gmaps.geocode(location)
    db = DB(get_db_conn())
    db.import_data()
    list_out = db.shapes_near_location(geoloc)
    db.conn.close()
    return list_out

def insert_data():
    db = DB(get_db_conn())
    #tableset = ["shapes", "elections"]
    try:
        db.create_tables()
        db.conn.close()
    except:
        logging.info("Table Creation Failed")
        db.conn.close()

@app.route('/t')
def detail():
    db = DB(get_db_conn())
    #db.import_data()

    location = "placeholder"
     
    #senate, x = db.nearby_voting_impact(location, "states")
    #logging.info(senate)
    #house, x1 = db.nearby_voting_impact(location, "house")
    #logging.info(house)
    #state_house, x2 = db.nearby_voting_impact(location, "state_leg")
    #ballot, x3 = db.nearby_voting_impact(location, "ballot")
    #presidential_vp = 20
    db.conn.close()
    return render_template("tabletest.html", mapbox_key = mapbox_key)

# Utilities ------------------------------

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
