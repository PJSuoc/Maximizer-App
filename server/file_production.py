from os import path
import subprocess
import logging
import sqlite3 as sqlite
import pandas as pd
import geopandas as gpd
from shapely import Point
from pathlib import Path
import sys
import json
import requests
import numpy as np
from static.data.gsheet_import import spreadsheet_pull
from config import sheet_id

STATEDICT = {
    "Alabama": "01","Alaska": "02", "Arizona": "04","Arkansas": "05", 
    "California": "06", "Colorado": "08", "Conneticut": "09", "Delaware": "10", "District of Columbia": "11",
    "Florida": "12", "Georgia": "13", "Hawaii": "15", "Idaho": "16", "Illinois": "17", 
    "Indiana": "18", "Iowa": "19", "Kansas": "20", "Kentucky": "21", 
    "Lousisiana": "22", "Maine": "23", "Maryland": "24", "Massachusetts": "25", 
    "Michigan": "26", "Minnesota": "27", "Mississippi": "28", "Missouri": "29", 
    "Montana": "30", "Nebraska": "31", "Nevada": "32", "New Hampshire": "33",
    "New Jersey": "34", "New Mexico": "35", "New York": "36", "North Carolina": "37", 
    "North Dakota": "38", "Ohio": "39", "Oklahoma": "40", "Oregon": "41", 
    "Pennsylvania": "42", "Rhode Island": "44", "South Carolina": "45", "South Dakota": "46", 
    "Tennessee": "47", "Texas": "48", "Utah": "49", "Vermont": "50", "Virginia": "51", 
    "Washington": "53", "West Virginia": "54", "Wisconsin": "55", "Wyoming": "56"
}

STATES = [ "Alabama","Alaska", "Arizona","Arkansas", "California", "Colorado", 
    "Conneticut", "Delaware", "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", 
    "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", 
    "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", 
    "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", 
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", 
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", 
    "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]



#Presidential Data CSV
p_file = "president.csv"
#Senate Data CSV
s_file = "senate.csv"
#House of Representatives CSV
h_file = "congress_house.csv"
#Governors CSV
g_file = "governor.csv"
#State Upper Legislature (State Senate) CSV
su_file = "state_upper_legislature.csv"
#State Lower Legislature (State House) CSV
sl_file = "state_lower_legislature.csv"
# Ballot Initiatives ()
b_file = "ballot_initiative.csv"
# Candidates
c_file = "candidates.csv"
file_list = [p_file, s_file, h_file, g_file, su_file, sl_file, b_file]

### Data Importing ##########################################################

import_loc = "static/data/csv_imports/"
# List of the sheet tab names used for each data component w/ data ranges
sheet_list = ['Presidential!A2:X','Senate!A2:X','House!A2:X','Governor!A2:X',
              'State Upper Legislature!A2:X','State Lower Legislature!A2:X',
              'Ballot Initiatives!A2:X','Candidates!A2:X']
# List of file locations matching list of sheet names
import_list = [p_file, s_file, h_file, g_file, su_file, sl_file, b_file, c_file]

#for i, sheet_name in enumerate(sheet_list):
#    file = spreadsheet_pull(sheet_id, sheet_name)


##### State VP Merger Test function #########################################
def state_vp(df):

    svp_df = p.copy(deep=True)
    svp_df["race_type"] = "Aggregate"
    df["voter_power"] = df["voter_power"].astype(float)

    for state in STATES:
        state_df = df[df["state_name"] == state]
        vpdf = state_df[state_df["voter_power"] >= 10]

        p_df = vpdf[vpdf["race_type"] == "Presidential"]
        p_vp = p_df.shape[0]
        s_df = vpdf[vpdf["race_type"] == "Senate"]
        s_vp = s_df.shape[0]
        h_df = vpdf[vpdf["race_type"] == "House"]
        h_vp = h_df.shape[0]
        g_df = vpdf[vpdf["race_type"] == "Governor"]
        g_vp = g_df.shape[0]
        su_df = vpdf[vpdf["race_type"] == "State Leg (Upper)"]
        su_vp = su_df.shape[0]
        sl_df = vpdf[vpdf["race_type"] == "State Leg (Lower)"]
        sl_vp = sl_df.shape[0]
        b_df = state_df[state_df["race_type"] == "Ballot Initiative"]
        b_vp = b_df.shape[0]

        # 3 points per su, sl, if(ballot)
        state_vp = (p_vp + s_vp + h_vp + g_vp + min(4, su_vp) + min(4, sl_vp) + min(3, b_vp))
        state_vp = round(state_vp * (100/15)) #Temporary VP Normalizer

        svp_df.loc[svp_df["state_name"] == state, ["voter_power"]] = state_vp
    
    return svp_df


### CSV Cleaner & Rewriter
# The CSV cleaners are VERY similar, candidate just trims to different fields
# and also has additional cleaning on election denier.

def election_csv_cleaner(location, csv_tag, destination, csv_name):
    df = pd.read_csv(location + csv_name)

    # Cut the CSV down to the relevant columns
    if csv_name != "ballot_initiative.csv":
        df = df[["state", "congress", "s_upper", "s_lower", "state_name", "race_type", "election_name", "voter_power", "D_running", "R_running"]]

    #state ID cleaning
    df["state"] = df["state"].fillna(0.0).astype(int)
    df["state"] = df["state"].astype(str)
    df["state"] = df["state"].str.zfill(2)
    
    # House of Representatives ID cleaning
    df["congress"] = df["congress"].astype(str)
    df["congress"] = df["congress"].str.zfill(2)

    # State Upper Legislature ID cleaning
    df["s_upper"] = df["s_upper"].astype(str)
    df["s_upper"] = df["s_upper"].str.zfill(3)

    # State Lower Legislature ID cleaning
    df["s_lower"] = df["s_lower"].astype(str)
    df["s_lower"] = df["s_lower"].str.zfill(3)

    # Voter Power Cleaning
    df["voter_power"] = df["voter_power"].astype(float)

    df.to_csv(destination + csv_tag + csv_name,  index = False)

def candidate_csv_cleaner(location, csv_tag, destination, csv_name):
    df = pd.read_csv(location + csv_name, dtype=str)

    # Cut the CSV down to the relevant columns
    df = df[["name", "party", "state", "congress", "s_upper", "s_lower", "state_name", "race_type", "election_name","election_denier","campaign_link","donation_link"]]

    #state ID cleaning
    df["state"] = df["state"].astype(str)
    df["state"] = df["state"].str.zfill(2)
    # House of Representatives ID cleaning
    df["congress"] = df["congress"].astype(str)
    df["congress"] = df["congress"].str.zfill(2)
    # State Upper Legislature ID cleaning
    #df["s_upper"] = df["s_upper"].astype(int)
    df["s_upper"] = df["s_upper"].astype(str)
    df["s_upper"] = df["s_upper"].str.zfill(3)
    # State Lower Legislature ID cleaning
    df["s_lower"] = df["s_lower"].astype(str)
    df["s_lower"] = df["s_lower"].str.zfill(3)
    # Other name cleaning
    df["name"] = df["name"].astype(str)
    df["name"] = df["name"].fillna("Unknown")
    df["party"] = df["party"].fillna("Unknown")
    df["election_denier"] = df["election_denier"].fillna(0)
    df["election_denier"] = df["election_denier"].astype(float).astype(int).astype(str)


    df.to_csv(destination + csv_tag + csv_name,  index = False)

### CSV Reader

def csv_reader(filename):
    #Currently unused
    df = pd.read_csv(destination + csv_tag + p_file)
    return df

### GeoJSON Writer
def geojson_writer(df, filename):
    # forces voter_power to a number for interpretation by color scale
    df["voter_power"] = df["voter_power"].astype(float)
    gdf = gpd.GeoDataFrame(df, crs=4269)
    desto = destination + geojson_tag + filename
    output_file = desto.replace('.geojson', '_albers.geojson')
    
    # Write the initial GeoJSON file
    gdf.to_file(desto, driver="GeoJSON")
    
    # Construct the command
    command = f'dirty-reproject --forward albersUsa < "{desto}" > "{output_file}"'
    
    print(f"Executing command: {command}")
    
    try:
        # Use shell=True to handle input/output redirection
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for the process to complete and capture output
        stdout, stderr = process.communicate()
        
        # Check the return code
        if process.returncode == 0:
            print(f"Successfully created Albers projection file: {output_file}")
        else:
            print(f"Error occurred. Return code: {process.returncode}")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
          
    except Exception as e:
        print(f"An exception occurred: {e}")
    

################################################################################
#####      CSV Production     ##################################################
################################################################################


##### CSVs utilized for various purposes #####

# These 2 are used to identify folders things are coming/going to/from
location = "static/data/csv_imports/"
destination = "static/data/calculated_files/"
# Secondary Folder
csv_tag = "csvs/"
geojson_tag = "geojsons/"


# Clean all CSVs and write them back
for df_file in file_list:
    election_csv_cleaner(location, csv_tag, destination, df_file)

# Clean candidate CSV and write it back
candidate_csv_cleaner(location, csv_tag, destination, c_file)

#Read in the cleaned CSVs
p = pd.read_csv(destination + csv_tag + p_file, dtype=str)
s = pd.read_csv(destination + csv_tag + s_file, dtype=str)
h = pd.read_csv(destination + csv_tag + h_file, dtype=str)
g = pd.read_csv(destination + csv_tag + g_file, dtype=str)
su = pd.read_csv(destination + csv_tag + su_file, dtype=str)
sl = pd.read_csv(destination + csv_tag + sl_file, dtype=str)
b = pd.read_csv(destination + csv_tag + b_file, dtype=str)
#e = pd.read_csv(destination + csv_tag + e_file, dtype=str) # state level elections officials


## Separates the ballot initiatives, and creates a state-level catchall category
b_dem = b[b["race_type"] == "Democracy Repair"]
b_dd = b[b["race_type"] == "Direct Democracy"]
b_rr = b[b["race_type"] == "Reproductive Rights"]
b_civ = b[b["race_type"] == "Civil Liberties"]
minor = g + b_dd + b_civ

merger_list = [p, s, h, g, su, sl, b]
merge_df = pd.concat(merger_list, ignore_index=True)

#Make aggregate rows for the states
svp_df = state_vp(merge_df)
merger_list.append(svp_df)

#Make a full elections set with the aggregates included (not sure if need)
elections_df = pd.concat(merger_list, ignore_index=True)

#write both options to a csv for future use
svp_df.to_csv("static/data/calculated_files/csvs/aggregate.csv",  index = False)
merge_df.to_csv("static/data/calculated_files/csvs/elections.csv",  index = False)


dem_file = "democracy.csv"

countcsv_list = []

def count_csv(df):
    for state in STATES:
        pass

################################################################################
#####      GeoJSON Production     ##############################################
################################################################################

congress = gpd.read_file("static/data/shp_imports/cb_2023_us_cd118_500k/cb_2023_us_cd118_500k.shp") # static/data/shp_imports/congress/lawsuit_congressional/modified_congressional.shp
congress = congress.to_crs(4269)
states = gpd.read_file("static/data/shp_imports/cb_2023_us_state_500k/cb_2023_us_state_500k.shp")
states = states.to_crs(4269)
state_upper = gpd.read_file("static/data/shp_imports/cb_2023_us_sldu_500k/cb_2023_us_sldu_500k.shp") # static/data/shp_imports/upper_leg/modified_leg_upper/national_2024_elections_st_leg_upper_boundaries_modified.shp
state_upper = state_upper.to_crs(4269)
state_lower = gpd.read_file("static/data/shp_imports/cb_2023_us_sldl_500k/cb_2023_us_sldl_500k.shp") # static/data/shp_imports/lower_leg/modified_leg_lower/national_2024_elections_st_leg_lower_boundaries_modified.shp
state_lower = state_lower.to_crs(4269)

def regshapeimport(states, congress, state_upper, state_lower):
    # Imports the individual shapefiles and cleans their shape identifiers to match the
    # 4 columns used by our database to sort elections based on different shapes.
    # Returns all 4 types of shapes as geodataframes
    congress["state"] = congress["STATEFP"]
    congress["congress"] = congress["CD118FP"]
    congress["s_upper"] = ""
    congress["s_lower"] = ""
    states["state"] = states["STATEFP"]
    states["congress"] = ""
    states["s_upper"] = ""
    states["s_lower"] = ""
    state_upper["state"] = state_upper["STATEFP"]
    state_upper["congress"] = ""
    state_upper["s_upper"] = state_upper["SLDUST"]
    state_upper["s_lower"] = ""
    state_lower["state"] = state_lower["STATEFP"]
    state_lower["congress"] = ""
    state_lower["s_upper"] = ""
    state_lower["s_lower"] = state_lower["SLDLST"]
    return states, congress, state_upper, state_lower


def all_shape_maker(states, congress, state_upper, state_lower):
    c_clip = congress[["state", "congress", "s_upper", "s_lower", "geometry"]]
    s_clip = states[["state", "congress", "s_upper", "s_lower", "geometry"]]
    u_clip = state_upper[["state", "congress", "s_upper", "s_lower", "geometry"]]
    l_clip = state_lower[["state", "congress", "s_upper", "s_lower", "geometry"]]

    df_list = [c_clip, s_clip, u_clip, l_clip]
    all_df = gpd.GeoDataFrame(pd.concat(df_list, ignore_index=True), crs=df_list[0].crs)
    return all_df

states, congress, state_upper, state_lower = regshapeimport(states, congress, state_upper, state_lower)
all_df = all_shape_maker(states, congress, state_upper, state_lower)

## Uncomment this line to update all_shapes
#all_df.to_file("static/data/calculated_files/geojsons/all_shapes/all_shapes.shp")

# race_type names that are relevant for certain things
taglist = ["Aggregate", "Presidential","Senate","House", "Governor", "State Leg (Upper)",
        "State Leg (Lower)", "Ballot Initiative", "democracy", "rrights", "statelevel"]
a_json = "aggregate.geojson"
p_json = "president.geojson"
s_json = "senate.geojson"
h_json = "congress_house.geojson"
g_json = "governor.geojson"
su_json = "state_upper_legislature.geojson"
sl_json = "state_lower_legislature.geojson"
b_json = "ballot_initiative.geojson"
dem_json = "democracy.geojson"
rr_json = "reprights.geojson"
slevel_json = "statewide.geojson"

# Function that standardizes DFs, shapes AND not shapes
def clean_df(df, tag):
    # Cleans dataframes so that columns are the correct types and nans don't exist
    df["state"] = df["state"].fillna("")
    df["state"] = df["state"].astype(str)
    df["congress"] = df["congress"].fillna("")
    df["congress"] = df["congress"].astype(str)
    df["s_upper"] = df["s_upper"].fillna("")
    df["s_upper"] = df["s_upper"].astype(str)
    df["s_lower"] = df["s_lower"].fillna("")
    df["s_lower"] = df["s_lower"].astype(str)
    #tag = 1 for election dataframes, 0 for shape dataframes
    if tag == 1:
        df["voter_power"] = df["voter_power"].astype(float)
        df["voter_power"] = df["voter_power"].fillna(0)
    return df

# List for creating the various geojsons
# I pull things in and out of the following list if I only want to update specific ones
shapemergelist = [svp_df, p, s, h, g, su, sl, b]
shp_choice_list = [states, states, states, congress, states, state_upper, state_lower, states]
json_list = [a_json, p_json, s_json, h_json, g_json, su_json, sl_json, b_json]

for i, df in enumerate(shapemergelist):
    # Gets both the election and shape dataframes
    df = clean_df(df, 1)
    shapes = clean_df(shp_choice_list[i], 0)
    print("Shapes:", df.shape[0], shapes.shape[0])
    print(i, json_list[i], taglist[i])
    # Merges them so that each shape stays, and election information is added if it exists and matches
    category_df = shapes.merge(df, how="left", on = ["state", "congress", "s_upper", "s_lower"])
    print("Before Filter:", category_df.shape[0])
    print("After Filter:", category_df.shape[0])
    geojson_writer(category_df, json_list[i])

#Creates GEOJSONS for things without voter power- raw counts
countmergelist = [b_dem, b_rr, minor]
shp_choice_list = [states, states, states]
json_list = [dem_json, rr_json, slevel_json]

#This needs to be modified to build the geojsons properly
for i, df in enumerate(countmergelist):
    df = clean_df(df, 1)
    shapes = clean_df(shp_choice_list[i], 0)
    print("Shapes:", df.shape[0], shapes.shape[0])
    print(i, json_list[i], taglist[i])
    # Merges them so that each shape stays, and election information is added if it exists and matches
    category_df = shapes.merge(df, how="left", on = ["state", "congress", "s_upper", "s_lower"])
    print("Before Filter:", category_df.shape[0])
    print("After Filter:", category_df.shape[0])
    geojson_writer(category_df, json_list[i])