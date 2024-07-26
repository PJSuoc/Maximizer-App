from os import path
import logging
import sqlite3 as sqlite
import pandas as pd
import geopandas as gpd
from shapely import Point
from pathlib import Path
import sys
import json

STATEDICT = {
    "Alabama": "01","Alaska": "02", "Arizona": "04","Arkansas": "05", 
    "California": "06", "Colorado": "08", "Conneticut": "09", "Delaware": "10", 
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

##### CSVs utilized for various purposes #####

#Presidential Data CSV
p_loc = "static/data/csv_imports/president.csv"
p = pd.read_csv(p_loc)
#Senate Data CSV
s_loc = "static/data/csv_imports/senate.csv"
s = pd.read_csv(s_loc)
#House of Representatives CSV

#Governors CSV

#State Upper Legislature (State Senate) CSV

#State Lower Legislature (State House) CSV


##### State VP Merger Test function #####
def vp_merger(p, s, h, g, su, sl, bi):
    
    state_vpdict = {}

    for state in STATEDICT:
        statevp = 0
        pres = p[p["state_name" == state]]
        sen = s[s["state_name" == state]]
        house = h[h["state_name" == state]]
        gov = g[g["state_name" == state]]
        upper = su[su["state_name" == state]]
        lower = sl[sl["state_name" == state]]
        ballot = bi[bi["state_name" == state]]

        presvp = pres["voter_power"]
        senvp = sen["voter_power"].sum()
        housevp = house["voter_power"].mean()
        govvp = gov["voter_power"]
        uppervp = upper["voter_power"].mean()
        lowervp = lower["voter_power"].mean()
        balvp = min(10, (ballot.shape[0]*5))

        statevp = (presvp * 0.2) + (senvp * 0.2) + (housevp * 0.2) +\
                    (govvp * 0.2) + (uppervp * 0.2) + (lowervp * 0.2) + balvp
        state_vpdict[state] = statevp
    #Maybe add rows to election called Aggregate
    return state_vpdict

def csv_cleaner(csv_name):
    df = pd.read_csv(csv_name)

    #state ID cleaning
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

    df.to_csv(csv_name)