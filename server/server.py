import json
import requests
import argparse
import sqlite3
import logging
from flask import (
    current_app,
    g,
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    Response,
    url_for,
)
import googlemaps
import geopandas as gpd
import pandas as pd
from datetime import datetime
import os
from pathlib import Path
import logging
import base64
from urllib.parse import urlparse, parse_qs
import re
from werkzeug.exceptions import BadRequest

# Other File imports: DB for database interaction, calculations, support.
from db import DB
from constants import STATES, STATELOC, POSTAL_TO_STATE, STATEDICT

## Sets environment variables based on locale
config_check = Path("config.py")
if config_check.is_file():
    ## Environment Variables in for local development
    from config import flask_key, google_key, mapbox_key, LOG_VIEW_SECRET_KEY
else:
    ## Environment Variables for heroku local or production
    flask_key = os.environ.get("flask_key")
    mapbox_key = os.environ.get("mapbox_key")
    google_key = os.environ.get("google_key")


# base setup
app = Flask(__name__)

# Ensure templates are auto-reloaded
# Set to False for production, True for development
app.config["TEMPLATES_AUTO_RELOAD"] = True
# I need to understand this functionality (I currently do not)
# required for consistent session(s)?

app.secret_key = flask_key
gmaps = googlemaps.Client(key=google_key)

# path to db
DATABASE = "powermax.db"

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

# Loading full ballot initiatives data, this might be temporary
if Path("config.py").is_file():  # Local testing
    BALLOT_INITIATIVES_PATH = Path("static/data/csv_imports/ballot_initiative.csv")
else:  # Heroku deployment
    BALLOT_INITIATIVES_PATH = Path("server/static/data/csv_imports/ballot_initiative.csv")

def load_ballot_initiatives():
    try:
        return pd.read_csv(BALLOT_INITIATIVES_PATH)
    except FileNotFoundError:
        print(f"Ballot initiatives file not found: {BALLOT_INITIATIVES_PATH}")
        return pd.DataFrame()  # Empty DataFrame if file not found

# Load the data when the server starts
BALLOT_INITIATIVES = load_ballot_initiatives()


# Website Home Page
@app.route("/", methods=["GET", "POST"])
def home():
    """
    Renders the homepage with optional test versions.
    Falls back to home.html if the specified template doesn't exist.
    """
    # Get the democracy repair data from ELECTIONS
    postal_codes = list(POSTAL_TO_STATE.keys())

    # Pre-filter the data
    democracy_data = ELECTIONS[ELECTIONS["race_type"] == "Democracy Repair"].to_dict(orient="records")
    abortion_data = ELECTIONS[ELECTIONS["race_type"] == "Reproductive Rights"].to_dict(orient="records")
    other_initiative_data = ELECTIONS[ELECTIONS["race_type"].isin(["Direct Democracy", "Liberties"])].to_dict(orient="records")
    house_data = ELECTIONS[ELECTIONS["race_type"] == "House"].to_dict(orient="records")
    senate_data = ELECTIONS[ELECTIONS["race_type"] == "Senate"].to_dict(orient="records")
    president_data = ELECTIONS[ELECTIONS["race_type"] == "Presidential"].to_dict(orient="records")
    governor_data = ELECTIONS[ELECTIONS["race_type"] == "Governor"].to_dict(orient="records")
    state_leg_upper_data = ELECTIONS[ELECTIONS["race_type"] == "State Leg (Upper)"].to_dict(orient="records")
    state_leg_lower_data = ELECTIONS[ELECTIONS["race_type"] == "State Leg (Lower)"].to_dict(orient="records")

    # Default to home.html if no test version specified or if the file doesn't exist
    return render_template(
        "home.html",
        democracy_data=democracy_data,
        abortion_data=abortion_data,
        other_initiative_data=other_initiative_data,
        house_data=house_data,
        senate_data=senate_data,
        president_data=president_data,
        governor_data=governor_data,
        state_leg_upper_data=state_leg_upper_data,
        state_leg_lower_data=state_leg_lower_data,
        state_to_number=STATEDICT,
        postal_codes=postal_codes,
        mapbox_key=mapbox_key,
    )


@app.route("/local", methods=["GET", "POST"])
def local_elections():
    try:
        location = request.values.get("location") or request.args.get("location")
        if not location:
            flash("Please provide a location.", "error")
            return redirect("/")

        location = gmaps.geocode(location)
        return election_delivery_function_structured(location)
    except Exception as e:
        logging.error(f"Error in local_elections: {str(e)}")
        flash(
            "An error occurred while processing your request. Please try again.",
            "error",
        )
        return redirect("/")


@app.route("/state", methods=["GET", "POST"])
def state_elections():
    location = request.args.get("location")
    selection = request.args.get("selection", default="house")
    if location:
        # Check if it's a postal code
        if len(location) == 2 and location.upper() in POSTAL_TO_STATE:
            # Look up the full state name
            location = POSTAL_TO_STATE[location.upper()]

        return election_delivery_function_structured(location, selection)
    return redirect("/")


@app.route("/voter-power", methods=["GET", "POST"])
# It's the vp infographic page.
def vp_load():
    return render_template("vp.html")


@app.route("/about", methods=["GET", "POST"])
# It's the about page.
def about_load():
    return render_template("about.html")


@app.route("/faq", methods=["GET", "POST"])
# It's the FAQ page.
def faq_load():
    return render_template("faq.html")


@app.route("/feedback", methods=["GET", "POST"])
# It's the feedback page.
def feedback_load():
    return render_template("feedback.html")


@app.route("/view_logs")
def view_logs():
    secret_key = request.args.get("key")
    if secret_key != LOG_VIEW_SECRET_KEY:
        return jsonify({"error": "Access denied"}), 403

    try:
        with open("missing_data.log", "r") as log_file:
            logs = json.load(log_file)
        recent_logs = logs[-100:][::-1]
        return jsonify(recent_logs)  # Return last 100 log entries
    except FileNotFoundError:
        return jsonify({"error": "Log file not found"}), 404


@app.route("/get-involved", methods=["GET", "POST"])
def get_involved():
    try:
        if request.method == "POST":
            candidates = request.form.get("candidates")
            election = request.form.get("election")
        elif request.method == "GET":
            candidates = request.args.get("candidates")
            election = request.args.get("election")
        else:
            raise BadRequest("Invalid request method")

        # Validate and sanitize inputs
        if candidates:
            candidates = validate_candidates(candidates)
        if election:
            election = validate_election(election)

        db = DB()
        db.grab_dataframes(ELECTIONS, ALLSHAPES, CANDIDATES)

        # Use parameterized queries in your DB class methods
        elections_df = db.get_election_by_id(election)
        candidates_df = db.get_candidates_by_ids(candidates)
        if len(elections_df) == 0 or len(candidates_df) == 0:
            flash(
                "Election data not found. Error has been logged and will be corrected soon",
                "error",
            )
            return render_template("layout.html")

        return render_template(
            "getinvolved.html", candidates=candidates_df, election=elections_df
        )
    except Exception as e:
        app.logger.error(f"Error in get_involved: {str(e)}")
        print(f"Error in get_involved: {str(e)}")
        flash("An error occurred. Please try again later.", "error")
        return render_template("layout.html")

def validate_candidates(candidates):
    if isinstance(candidates, str):
        candidates = candidates.split(",")
    if not isinstance(candidates, list):
        raise ValueError(
            "Candidates must be a list or comma-separated string of integers"
        )
    return [int(c) for c in candidates if c.isdigit()]


def validate_election(election):
    if not re.match(r"^\d+$", str(election)):
        raise ValueError("Election must be an integer")
    return int(election)


# Utilities ------------------------------


def election_delivery_function(location):
    """
    Takes a location and returns the elections that are related to those shapes.
    For an exact location, returns elections within ~50 miles.
    For a state, returns elections within that state.

    """
    db = DB()
    db.grab_dataframes(ELECTIONS, ALLSHAPES, CANDIDATES)

    # Dictionary to store information from shape lookup
    lookup_dict = {"elections": {}, "layers": {}}
    lookup_components = [
        "Presidential",
        "Senate",
        "House",
        "Governor",
        "State Leg (Upper)",
        "State Leg (Lower)",
        "Democracy Repair",
        "State Level",
    ]

    election_count = 0  # Used for setting up election detail buttons
    # Gets information to place in dictionary
    for i in lookup_components:
        Nelections, shapelayer, election_count = db.nearby_voting_impact(
            location, i, election_count
        )
        lookup_dict["elections"][i] = Nelections
        lookup_dict["layers"][i] = shapelayer

    # Get Lat/Long coordinates for centering
    if type(location) != type([]):
        lat = STATELOC[location]["lat"]
        long = STATELOC[location]["long"]
    else:
        lat = location[0]["geometry"]["location"]["lat"]
        long = location[0]["geometry"]["location"]["lng"]

    # All the individual pieces for the detail lookup. May need to add vals
    # for zoom and center for the map as well, depending on address lookup
    return render_template(
        "detail.html",
        all_data=lookup_dict["elections"],
        pres_list=lookup_dict["elections"]["Presidential"],
        senate_list=lookup_dict["elections"]["Senate"],
        house_list=lookup_dict["elections"]["House"],
        state_house_list=lookup_dict["elections"]["State Leg (Lower)"],
        state_senate_list=lookup_dict["elections"]["State Leg (Upper)"],
        governor_list=lookup_dict["elections"]["Governor"],  # clear
        # ballot_list = lookup_dict["elections"]["Ballot Initiative"], #clear
        dem_ballot_list=lookup_dict["elections"]["Democracy Repair"],
        state_level_list=lookup_dict["elections"]["State Level"],
        pres_layer=lookup_dict["layers"]["Presidential"],
        senate_layer=lookup_dict["layers"]["Senate"],
        house_layer=lookup_dict["layers"]["House"],
        s_house_layer=lookup_dict["layers"]["State Leg (Lower)"],
        s_sen_layer=lookup_dict["layers"]["State Leg (Upper)"],
        governor_layer=lookup_dict["layers"]["Governor"],  # clear
        # ballot_layer = lookup_dict["layers"]["Ballot Initiative"], #clear
        dem_ballot_layer=lookup_dict["layers"]["Democracy Repair"],
        state_level_layer=lookup_dict["layers"]["State Level"],
        lat=lat,
        long=long,
        mapbox_key=mapbox_key,
    )


def election_delivery_function_structured(location, selection=None):
    db = DB()
    db.grab_dataframes(ELECTIONS, ALLSHAPES, CANDIDATES)

    # Dictionary to store information from shape lookup
    lookup_dict = {"elections": {}, "layers": {}}
    lookup_components = [
        "Presidential",
        "Senate",
        "House",
        "Governor",
        "State Leg (Upper)",
        "State Leg (Lower)",
        "Democracy Repair",
        "State Level",
    ]

    election_count = 0  # Used for setting up election detail buttons
    # Gets information to place in dictionary
    for i in lookup_components:
        elections_data, shapelayer, election_count = db.nearby_voting_impact_structured(
            location, i, election_count
        )
        lookup_dict["elections"][i] = elections_data
        lookup_dict["layers"][i] = shapelayer

    # Get Lat/Long coordinates for centering
    if type(location) != type([]):
        lat = STATELOC[location]["lat"]
        long = STATELOC[location]["long"]
    else:
        lat = location[0]["geometry"]["location"]["lat"]
        long = location[0]["geometry"]["location"]["lng"]

    # Convert BALLOT_INITIATIVES to a dictionary
    ballot_initiatives = BALLOT_INITIATIVES.to_dict(orient="records")
    
    return render_template(
        "detail.html",
        pres_list=lookup_dict["elections"]["Presidential"],
        senate_list=lookup_dict["elections"]["Senate"],
        house_list=lookup_dict["elections"]["House"],
        state_house_list=lookup_dict["elections"]["State Leg (Lower)"],
        state_senate_list=lookup_dict["elections"]["State Leg (Upper)"],
        governor_list=lookup_dict["elections"]["Governor"],
        dem_ballot_list=lookup_dict["elections"]["Democracy Repair"],
        state_level_list=lookup_dict["elections"]["State Level"],
        pres_layer=lookup_dict["layers"]["Presidential"],
        senate_layer=lookup_dict["layers"]["Senate"],
        house_layer=lookup_dict["layers"]["House"],
        s_house_layer=lookup_dict["layers"]["State Leg (Lower)"],
        s_sen_layer=lookup_dict["layers"]["State Leg (Upper)"],
        governor_layer=lookup_dict["layers"]["Governor"],
        dem_ballot_layer=lookup_dict["layers"]["Democracy Repair"],
        state_level_layer=lookup_dict["layers"]["State Level"],
        all_data=ELECTIONS.to_dict(orient="records"),
        ballot_initiatives=ballot_initiatives,
        state_to_number=STATEDICT,
        lat=lat,
        long=long,
        mapbox_key=mapbox_key,
        location=location,
        selection=selection,
    )


def write_to_log(message, log_type="info"):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": log_type,
        "message": message,
    }

    try:
        with open("missing_data.log", "r+") as log_file:
            logs = json.load(log_file)
            logs.append(log_entry)
            log_file.seek(0)
            json.dump(logs, log_file)
    except FileNotFoundError:
        with open("missing_data.log", "w") as log_file:
            json.dump([log_entry], log_file)


# Default Hostname/address code for temporary testing purposes
# Logging settings for log debugging
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", help="Server hostname (default 127.0.0.1)", default="127.0.0.1"
    )
    parser.add_argument(
        "-p",
        "--port",
        help="Server port (default 5000)",
        default=5000,
    )
    parser.add_argument(
        "-l",
        "--log",
        help="Set the log level (debug,info,warning,error)",
        default="warning",
        choices=["debug", "info", "warning", "error"],
    )
    parser.add_argument(
        "-d",
        "--dev",
        help="Configuration host spot options",
        default="dev",
        choices=["dev", "prod"],
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    # The format for our logger
    log_fmt = "%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"

    # Create the parser argument object
    args = parser.parse_args()
    if args.log == "debug":
        logging.basicConfig(format=log_fmt, level=logging.DEBUG)
        logging.debug("Logging level set to debug")
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.DEBUG)
    elif args.log == "info":
        logging.basicConfig(format=log_fmt, level=logging.INFO)
        logging.info("Logging level set to info")
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.INFO)
    elif args.log == "warning":
        logging.basicConfig(format=log_fmt, level=logging.WARNING)
        logging.warning("Logging level set to warning")
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.WARNING)
    elif args.log == "error":
        logging.basicConfig(format=log_fmt, level=logging.ERROR)
        logging.error("Logging level set to error")
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

    # I really would prefer this be a sysarg but I don't know enough about them to make it work
    if not config_check.is_file():
        print("And I ask myself- well, how did I get here?")
        args.port = int(os.environ.get("PORT", 5000))
        args.host = "0.0.0.0"

    # Store the address for the web app
    # app.config['addr'] = "http://%s:%s" % (args.host, args.port)
    print("Port it needs to use: ", int(os.environ.get("PORT", 5000)))

    logging.info("Starting Up!")
    print("STARTING with:", args.host, args.port)
    app.run(
        host=args.host, port=args.port, threaded=False, debug=args.debug
    )  # pulled out: