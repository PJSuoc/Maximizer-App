import os
import logging
import sqlite3 as sqlite
import pandas as pd
import geopandas as gpd
from shapely import Point
import pathlib
from pathlib import Path
import sys
import json
import platform

STATEDICT = {
    "Alabama": "01","Alaska": "02", "Arizona": "04","Arkansas": "05", 
    "California": "06", "Colorado": "08", "Connecticut": "09", "Delaware": "10", 
    "Florida": "12", "Georgia": "13", "Hawaii": "15", "Idaho": "16", "Illinois": "17", 
    "Indiana": "18", "Iowa": "19", "Kansas": "20", "Kentucky": "21", 
    "Louisiana": "22", "Maine": "23", "Maryland": "24", "Massachusetts": "25", 
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
# File pathways for Production function
if Path("config.py").is_file(): # Pathways for local testing
    allshape_path = Path("static/data/shp_imports/all_shapes/all_shapes.shp")
    candidate_path = Path("static/data/calculated_files/csvs/candidates.csv")
    #Switch these over to just the election csv ??
    president_path = Path("static/data/calculated_files/csvs/president.csv")
    senate_path = Path("static/data/calculated_files/csvs/senate.csv")
    house_path = Path("static/data/calculated_files/csvs/congress_house.csv")
    governor_path = Path("static/data/calculated_files/csvs/governor.csv")
    s_upper_path = Path("static/data/calculated_files/csvs/state_upper_legislature.csv")
    s_lower_path = Path("static/data/calculated_files/csvs/state_lower_legislature.csv")
    ballot_path = Path("static/data/calculated_files/csvs/ballot_initiative.csv")
else: # slightly adjusted pathways for Heroku deployment
    allshape_path = Path("server/static/data/shp_imports/all_shapes/all_shapes.shp")
    candidate_path = Path("server/static/data/calculated_files/csvs/candidates.csv")
    president_path = Path("server/static/data/calculated_files/csvs/president.csv")
    senate_path = Path("server/static/data/calculated_files/csvs/senate.csv")
    house_path = Path("server/static/data/calculated_files/csvs/congress_house.csv")
    governor_path = Path("server/static/data/calculated_files/csvs/governor.csv")
    s_upper_path = Path("server/static/data/calculated_files/csvs/state_upper_legislature.csv")
    s_lower_path = Path("server/static/data/calculated_files/csvs/state_lower_legislature.csv")
    ballot_path = Path("server/static/data/calculated_files/csvs/ballot_initiative.csv")


## Filepath Debugging Code
'''
p1 = Path("config.py")
print("Existence:", os.path.exists(p1))
if p1.is_file():
    print("Found this file:", p1)
else:
    print("Did not find p1:", p1)
'''

class DB:
    def __init__(self):
        pass
    
    def import_data_v2(self):
        '''
        Imports all necessary data into pandas/geopandas dataframes to hold in memory
        for website calculations.
        '''
        # Elections CSVs, separated for ease of maintenance/updates
        president = pd.read_csv(president_path, dtype=str)
        senate = pd.read_csv(senate_path, dtype=str)
        congress = pd.read_csv(house_path, dtype=str)
        governor = pd.read_csv(governor_path, dtype=str)
        s_upper = pd.read_csv(s_upper_path, dtype=str)
        s_lower = pd.read_csv(s_lower_path, dtype=str)
        ballot = pd.read_csv(ballot_path, dtype=str)
        # Merges election CSVs into a single dataframe for calculations
        df_list = [president, senate, congress, governor, s_upper, s_lower, ballot]
        self.elections = pd.concat(df_list, ignore_index=True)
        # Elections data cleaning/adjusting
        self.elections["eid"] = self.elections.index
        self.elections["state"] = self.elections["state"].fillna("")
        self.elections["congress"] = self.elections["congress"].fillna("")
        self.elections["s_upper"] = self.elections["s_upper"].fillna("")
        self.elections["s_lower"] = self.elections["s_lower"].fillna("")
        self.elections["election_name"] = self.elections["election_name"].fillna("")
        self.elections["voter_power_val"] = self.elections["voter_power"].astype(float)
        self.elections["voter_power"] = self.elections["voter_power"].fillna("N/A")
        
        # Candidates CSV
        self.candidates = pd.read_csv(candidate_path, dtype=str)
        self.candidates["cid"] = self.candidates.index
        self.candidates["state"] = self.candidates["state"].fillna("")
        self.candidates["congress"] = self.candidates["congress"].fillna("")
        self.candidates["s_upper"] = self.candidates["s_upper"].fillna("")
        self.candidates["s_lower"] = self.candidates["s_lower"].fillna("")
        self.candidates["name"] = self.candidates["name"].fillna("")
        self.candidates["party"] = self.candidates["party"].fillna("")

        # All Shapes shapefile for locating elections
        self.allshapes = gpd.read_file(allshape_path)
        self.allshapes["state"] = self.allshapes["state"].fillna("")
        self.allshapes["congress"] = self.allshapes["congress"].fillna("")
        self.allshapes["s_upper"] = self.allshapes["s_upper"].fillna("")
        self.allshapes["s_lower"] = self.allshapes["s_lower"].fillna("")

        elections = self.candidate_merger()

        return elections, self.allshapes, self.candidates


    def grab_dataframes(self, elections, allshapes, candidates):
        # Pulls dataframes from memory to use for calculation
        self.elections = elections
        print("electlen", elections.shape[0])
        self.allshapes = allshapes
        self.candidates = candidates

    def nearby_voting_impact(self, location, layer, fmid):
        '''
        Function set for getting the input layers for a specific geolocation
        fmid: int that is used for elements of the detail page, required to get
            unique links in place for each election
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

        election_string, fmid = self.detail_list_constructor(clean_elections, fmid)

        # Converts specific election types shapes to geojson for MapBox
        clean_elections.reset_index(drop = True)
        #print("name type", type(clean_elections.loc[0]["state_name"]))
       
        clean_elections = gpd.GeoDataFrame(clean_elections, crs=4269)
        layerjson = clean_elections.to_json()
        return election_string, layerjson, fmid
    
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
        # Does some work slicing things together that are deemed less relevant for State Level
        if layer == "State Level":
            partone = relevant[relevant["race_type"] == "Governor"]
            parttwo = relevant[relevant["race_type"] == "Direct Democracy"]
            partthree = relevant[relevant["race_type"] == "Civil Liberties"]
            partfour = relevant[relevant["race_type"] == "Reproductive Rights"]
            merger_list = [partone, parttwo, partthree, partfour]
            relevant = pd.concat(merger_list, ignore_index=True)
            print(relevant.shape[0])
        else:
            relevant = relevant[relevant["race_type"] == layer]

        if layer != "State Level" and layer != "Democracy Repair":
            # Filters elections by voter power 
            relevant = relevant[relevant["voter_power_val"] > 10]
            # Sorts remaining elections by voter power & get only the top 3
            relevant.sort_values("voter_power_val", inplace = True, ascending = False)
            relevant = relevant.reset_index(drop = True)
            output = relevant[0:5]
        elif layer == "State Level":
            #Attempting to deal with a category that has some VP and some non-vp
            '''
            relevant_gov = relevant[relevant["race_type"] == "Governor"]
            relevant_gov = relevant_gov[relevant_gov["voter_power_val"] > 10]
            relevant_ballot = relevant[relevant["race_type"] != "Governor"]
            rel_clean = pd.concat([relevant_gov, relevant_ballot], ignore_index=True)
            rel_clean.sort_values("voter_power_val", inplace = True, ascending = False)
            rel_clean = rel_clean.reset_index(drop = True)'''
            output = relevant[0:5]
        else:
            output = relevant
        
        return output
    
    def detail_list_constructor(self, election_list,form_id):
        '''
        Function designed to construct the set of list items that go in a category
        based off of the set of elections that you want to include

        Input: Election_list, pandas dataframe of elections to include
        Output: (very long) html/js string inserted into the webpage
        '''
        election_front = '<li class="list-group-item" id="detail-li"><div class="row" id="detail-row">'
        button_front = '<form action="/get-involved" id="'
        button_mid = '" method="post"><input type="hidden" name="candidates" value="'
        elec_btn_info =  '"><input type="hidden" name="election" value="'
        button_mid2 = '"><button class="btn btn-primary" type="submit" form="'
        button_back = '" value="Submit">Learn More</button></form></div></div></li>'
        name_front = '<div class="col" id="row-state">'
        elec_front = '<div class="col" id="row-election">'
        vp_front = '<div class="col" id="row-vp">'
        btn_front = '<div class="col" id="row-btn">'
        item_back = '</div>'
        completed_string = ''
        vpstr = "Voter Power: "
        

        for i, election in election_list.iterrows():
            state_name = election["state_name"]
            election_name = election["election_name"]
            election_vp = election["voter_power"]
            cand_list = str(election["candidate_ids"])
            #Makes a unique id for each election's secondary page
            fmid = "form_" + str(form_id)
            estr = str(state_name + " " + election_name)
            logging.info(cand_list)
            election_str = name_front + state_name + item_back + \
                            elec_front + election_name + item_back + \
                            vp_front + vpstr + election_vp + item_back + \
                            btn_front + button_front + fmid + button_mid + \
                            cand_list + elec_btn_info + estr + button_mid2 + fmid + button_back
            completed_string = completed_string + election_front + election_str
            form_id += 1 
        return completed_string, form_id
    
    def candidate_link_strings(self, candidate_ids):
        '''
        Generates the raw HTML for each candidate on the get involved page.
        Consists of:
            Overall Column: id=candidate
                List of elements: id=infolist
                    Candidate Name: id=cand
                    Candidate Party: id=cand
                    Candidate Campaign Button: id=campbtn
        
        Input: candidate_ids, list of candidates based off of unique id to include
        Output: (very long) html/js string inserted into the webpage
        '''
        # HTML Elements that get cobbled together
        cand_front = '<div class="col" id="candidate"><ul id="infolist" class="list-group-item">'
        name_front = '<li id="cand">'
        party_front = '<li id="cand">'
        button_front = '<li id="campbtn"><a class="btn btn-primary" href="'
        button_back = '" role="button">More information</a>'
        item_back = '</li>'
        cand_back = '</ul></div>'
        denier_text = '<li id="denier"><b>Skeptic Flag:</b> This candidate has made statements doubting \
            the electoral proceedings of free and fair elections in the United States. However, American \
            elections are among the best-administered in the world. For more on such claims, \
            see electiondeniers.org.</li>'

        candidate_link_string = ''
        #Creates each candidate individually and then puts them together
        for candidate in candidate_ids:
            id = int(candidate)
            name = self.candidates.loc[id]["name"]
            party = self.candidates.loc[id]["party"]
            camp_link = str(self.candidates.loc[id]["campaign_link"])
            denier = self.candidates.loc[id]["election_denier"]

            # Inserts warning about election deniers. I'd make it a popup, but that's a lot harder and time is of the essence.
            if denier == "1":
                c_str = cand_front + party_front + party + item_back + name_front + name + item_back + \
                    denier_text + button_front + camp_link + button_back + item_back
            else:
                c_str = cand_front + party_front + party + item_back + name_front + name + item_back + \
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
                
                # Does additional filtration for Ballot Initiatives
                # Otherwise just gets candidate matches for that election
                if election["race_type"] == "Democracy Repair" or election["race_type"] == "Reproductive Rights" or \
                election["race_type"] == "Civil Liberties" or election["race_type"] == "Direct Democracy":
                    matched = matcher[matcher["eid"] == election["eid"]]
                    matched = matched[matched["election_name_y"] == election["election_name"]]
                else:
                    matched = matcher[matcher["eid"] == election["eid"]]

                cand_id_list.append(list(matched["cid"]))

                # Explicitly for adding a string to geojsons
                candstring = ""
                for j, match in matched.iterrows():
                    candstring = candstring + " " + match["party"] + ": " + match["name"]
                cand_str_list.append(candstring)
        
        
        self.elections["candidate_ids"] = cand_id_list
        self.elections["candidate_names"] = cand_str_list
        return self.elections #with candidates