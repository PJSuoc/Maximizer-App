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

"""
Class for building database functionalities.
"""

class DB:
    def __init__(self, connection):
        self.conn = connection
    
    def import_data(self):
        '''
        Imports all necessary shapefiles for calculations.
        '''
        #self.states = gpd.read_file("./static/data/shp_imports/cb_2023_us_state_500k/cb_2023_us_state_500k.shp")
        #self.congress = gpd.read_file("./static/data/shp_imports/cb_2023_us_cd118_500k/cb_2023_us_cd118_500k.shp")
        #self.s_upper = gpd.read_file("./static/data/shp_imports/cb_2023_us_sldu_500k/cb_2023_us_sldu_500k.shp")
        #self.s_lower = gpd.read_file("./static/data/shp_imports/cb_2023_us_sldl_500k/cb_2023_us_sldl_500k.shp")
        self.allshapes = gpd.read_file("./static/data/shp_imports/all_shapes/all_shapes.shp")
        self.elections = pd.read_csv("./static/data/csv_imports/fakedata.csv", dtype=str)

        #Clean NA's from imported shape matching files
        self.elections["state"] = self.elections["state"].fillna("")
        self.elections["congress"] = self.elections["congress"].fillna("")
        self.elections["s_upper"] = self.elections["s_upper"].fillna("")
        self.elections["s_lower"] = self.elections["s_lower"].fillna("")
        self.elections["voter_power_val"] = self.elections["voter_power"].astype(float)
        self.elections["voter_power"] = self.elections["voter_power"].fillna("N/A")
        self.allshapes = self.allshapes.fillna("")
        return self.elections, self.allshapes
    
    def import_data_v2(self):
        '''
        Imports all necessary data into pandas/geopandas dataframes to hold in memory
        for website calculations.
        '''
        # Elections CSVs, separated for ease of maintenance/updates
        president = pd.read_csv("static/data/csv_imports/president.csv", dtype=str)
        senate = pd.read_csv("static/data/csv_imports/senate.csv", dtype=str)
        congress = pd.read_csv("static/data/csv_imports/congress_house.csv", dtype=str)
        s_upper = pd.read_csv("static/data/csv_imports/state_upper_legislature.csv", dtype=str)
        s_lower = pd.read_csv("static/data/csv_imports/state_lower_legislature.csv", dtype=str)
        ballot = pd.read_csv("static/data/csv_imports/ballot_initiative.csv", dtype=str)
        # Merges election CSVs into a single dataframe for calculations
        df_list = [president, senate, congress, s_upper, s_lower, ballot]
        self.elections = pd.concat(df_list, ignore_index=True)
        # Elections data cleaning/adjusting
        self.elections["eid"] = self.elections.index
        self.elections["state"] = self.elections["state"].fillna("")
        self.elections["congress"] = self.elections["congress"].fillna("")
        self.elections["s_upper"] = self.elections["s_upper"].fillna("")
        self.elections["s_lower"] = self.elections["s_lower"].fillna("")
        self.elections["district_name"] = self.elections["district_name"].fillna("")
        self.elections["voter_power_val"] = self.elections["voter_power"].astype(float)
        self.elections["voter_power"] = self.elections["voter_power"].fillna("N/A")
        
        # Candidates CSV
        self.candidates = pd.read_csv("static/data/csv_imports/candidates.csv", dtype=str)
        self.candidates["cid"] = self.candidates.index
        self.candidates["state"] = self.candidates["state"].fillna("")
        self.candidates["congress"] = self.candidates["congress"].fillna("")
        self.candidates["s_upper"] = self.candidates["s_upper"].fillna("")
        self.candidates["s_lower"] = self.candidates["s_lower"].fillna("")

        # All Shapes shapefile for locating elections
        self.allshapes = gpd.read_file("./static/data/shp_imports/all_shapes/all_shapes.shp")
        self.allshapes["state"] = self.allshapes["state"].fillna("")
        self.allshapes["congress"] = self.allshapes["congress"].fillna("")
        self.allshapes["s_upper"] = self.allshapes["s_upper"].fillna("")
        self.allshapes["s_lower"] = self.allshapes["s_lower"].fillna("")

        elections = self.candidate_merger()

        return elections, self.allshapes, self.candidates


    def grab_dataframes(self, elections, allshapes, candidates):
        # Pulls dataframes from memory to use for calculation
        self.elections = elections
        self.allshapes = allshapes
        self.candidates = candidates

    def nearby_voting_impact(self, location, layer):
        '''
        Function set for getting the input layers for a specific geolocation
        '''

        # Gets nearby shapes to location input
        if type(location) == type([]):
            # IF Address input is a specific geolocation (comes out as type list)
            nearby_shapes = self.shapes_near_location(location)
        else:
            # IF a state is selected from a dropdown menu
            nearby_shapes = self.shapes_in_state(location)

        
        # Get the set of elections for the shapes and filter them for the output
        clean_elections = self.voter_power_filter(nearby_shapes, layer)
        
        election_string = self.detail_list_constructor(clean_elections)

        # Converts specific election types shapes to geojson for MapBox
        clean_elections.reset_index(drop = True)
        #print("name type", type(clean_elections.loc[0]["state_name"]))
        print("list type", clean_elections.columns.values)
        print("all type", clean_elections.dtypes)
        print("all type", clean_elections.shape)
        print("overall type", type(clean_elections))
        clean_elections = gpd.GeoDataFrame(clean_elections, crs=4269)
        layerjson = clean_elections.to_geo_dict(drop_id = True)
        return election_string, layerjson
    
    def shapes_near_location(self, location):
        shape = self.allshapes # Temporary, in the future will be the mergeset of shapes

        #Code to allow for testing placeholder for location
        if location == "placeholder":
            location = Point((-74.6648071,40.3476804))
        else:
            lat = location[0]["geometry"]["location"]["lat"]
            lng = location[0]["geometry"]["location"]["lng"]
            location = Point((lng,lat))
        #logging.info(location)
        loc_df = gpd.GeoDataFrame(geometry=[location], crs=4269)
        loc_df = loc_df.to_crs(3857)
        loc_range = loc_df.buffer(80000) #80k meters is approx. 50 miles
        loc_range = loc_range.to_crs(4269)
        shape["close"] = shape.intersects(loc_range[0])
        return shape[shape["close"]==True]


    def shapes_in_state(self, state):
        
        state = STATEDICT[state]
        shapes_in_state = self.allshapes[self.allshapes["state"] == state]

        return shapes_in_state

    def voter_power_filter(self, shapelist, layer):

        # Filters elections based to ones in the nearby shapes
        relevant = shapelist.merge(self.elections, how="inner", 
                left_on =["state","congress","s_upper","s_lower"], 
                right_on = ["state","congress","s_upper","s_lower"])
        
        # Filters elections by the race type requested
        relevant = relevant[relevant["race_type"] == layer]

        if layer != "Ballot Initiative":
            # Filters elections by voter power 
            relevant = relevant[relevant["voter_power_val"] > 10]
            # Sorts remaining elections by voter power & get only the top 3
            relevant.sort_values("voter_power_val", inplace = True, ascending = False)
            relevant = relevant.reset_index(drop = True)
            output = relevant[0:3]
        else:
            output = relevant
        
        return output
    
    def output_formatter(self, list):
        removed_extras = list[["district_name","state","race_type","voter_power"]]
        return removed_extras
    
    def detail_list_constructor(self, election_list):
        '''
        Function designed to construct the set of list items that go in a category
        based off of the set of elections that you want to include

        Input: Election_list, pandas dataframe of elections to include
        Output: (very long) html/js string inserted into the webpage
        '''
        election_front = '<li class="list-group-item"><div class="row">'
        # The Button here is non-functional, and will need to be updated for actual links or simply removed for now.
        button_front = '<form action="/get-involved" id="gi" method="post"><input type="hidden" name="candidates" value="' 
        button_back = '"></form><button class="btn btn-primary" type="submit" form="gi" value="Submit">Get Involved</button></div></div></li>'
        item_front = '<div class="col">'
        item_back = '</div>'
        completed_string = ''
        statestr = "State: "
        vpstr = "Voter Power: "
        
        for i, election in election_list.iterrows():
            #logging.info(election)
            state_name = election["state"] + ", " + election["district_name"]
            election_vp = election["voter_power"]
            cand_list = str(election["candidate_ids"])
            #logging.info(cand_list)
            election_str = item_front + statestr + state_name + item_back + item_front + vpstr + election_vp + item_back + item_front + button_front + cand_list + button_back
            completed_string = completed_string + election_front + election_str 
        return completed_string
    
    def candidate_link_strings(self, candidate_ids):

        cand_front = '<div class="col" id="candidate"><ul class="list-group-item">'
        name_front = '<li id="cand">'
        party_front = '<li id="cand">'
        button_front = '<li id="cand"><a class="btn btn-primary" href="'
        button_back = '" role="button">Candidate Campaign</a>'
        item_back = '</li>'
        cand_back = '</ul></div>'

        candidate_link_string = ''
        #print(candidate_ids, type(candidate_ids))
        for candidate in candidate_ids:
            id = int(candidate)
            name = self.candidates.loc[id]["name"]
            party = self.candidates.loc[id]["party"]
            camp_link = self.candidates.loc[id]["campaign_link"]

            c_str = cand_front + name_front + name + item_back + party_front + party + item_back + \
                button_front + camp_link + button_back + item_back
            candidate_link_string = candidate_link_string + c_str + cand_back

        #candidate_link_string = candidate_link_string + cand_back
        return candidate_link_string # Long string of all candidate info boxes

    def candidate_merger(self):
        matcher = self.elections.merge(self.candidates, how="inner", 
                left_on =["state","congress","s_upper","s_lower","race_type"], 
                right_on = ["state","congress","s_upper","s_lower","race_type"])
        cand_id_list = []
        cand_str_list = []

        #creates lists of candidate ids and names/affiliations for each election
        for i, election in self.elections.iterrows():
                matched = matcher[matcher["eid"] == election["eid"]]
                cand_id_list.append(list(matched["cid"]))
                cand_str_list.append("cand " + matched["party"] + ": " + matched["name"])
        
        
        self.elections["candidate_ids"] = cand_id_list
        self.elections["candidate_names"] = cand_str_list
        return self.elections #with candidates