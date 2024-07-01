from os import path
import logging
import sqlite3 as sqlite
import pandas as pd
import geopandas as gpd
from shapely import Point
from pathlib import Path

"""
Class for building database functionalities.
"""

class DB:
    def __init__(self, connection):
        self.conn = connection
        # There are 4 initial layers of shapes:
        # 1. State shapes
        # 2. Congressional District Shapes
        # 3. State Legislature Shapes lower (State House, typically)
        # 4. State Legislature Shapes upper (Senate Senate, typically)

    def execute_script(self, script_file):
        """
        Runs sql scripts when given the file name
        """
        with open(script_file, "r") as script:
            c = self.conn.cursor()
            c.executescript(script.read())
            self.conn.commit()

    def create_tables(self):
        """
        Calls the schema sql files to create tables
        """
        script_file = path.join("schemas", "shapes.sql")
        self.execute_script(script_file)
        script_file = path.join("schemas", "elections.sql")
        self.execute_script(script_file)
    
    def import_data(self):
        '''
        Imports all necessary shapefiles for calculations.
        '''
        self.states = gpd.read_file("./static/data/cb_2023_us_state_500k/cb_2023_us_state_500k.shp")
        self.congress = gpd.read_file("./static/data/cb_2023_us_cd118_500k/cb_2023_us_cd118_500k.shp")
        self.s_upper = gpd.read_file("./static/data/cb_2023_us_sldu_500k/cb_2023_us_sldu_500k.shp")
        self.s_lower = gpd.read_file("./static/data/cb_2023_us_sldl_500k/cb_2023_us_sldl_500k.shp")
        self.allshapes = gpd.read_file("./static/data/all_shapes/all_shapes.shp")
        self.elections = pd.read_csv("./static/data/fakedata.csv", dtype=str)

        #Clean NA's from imported shape matching files
        self.elections["state"] = self.elections["state"].fillna("")
        self.elections["congress"] = self.elections["congress"].fillna("")
        self.elections["s_upper"] = self.elections["s_upper"].fillna("")
        self.elections["s_lower"] = self.elections["s_lower"].fillna("")
        self.elections["voter_power_val"] = self.elections["voter_power"].astype(float)
        self.allshapes = self.allshapes.fillna("")

    def nearby_voting_impact(self, location, layer):
        '''
        Function set for getting the input layers for a specific geolocation
        '''
        
        # Gets nearby shapes to location input
        if type(location) == type([]):
            # IF Address input is a specific geolocation (comes out as type list)
            nearby_shapes = self.shapes_near_location(location, layer)
        else:
            # IF a state is selected from a dropdown menu
            nearby_shapes = self.shapes_in_state(location, layer)

        near_close_elections = self.voter_power_filter(nearby_shapes, layer)
        clean_elections = self.output_formatter(near_close_elections)
        election_string = self.detail_list_constructor(clean_elections)

        # Converts specific election types shapes to geojson for MapBox
        shapes_json = near_close_elections.to_json(default_handler=str)
        return election_string, shapes_json
    
    def shapes_near_location(self, location, layer):
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

    def voter_power_filter(self, shapelist, layer):

        # Filters elections based to ones in the nearby shapes
        relevant = self.elections.merge(shapelist, how="inner", 
                left_on =["state","congress","s_upper","s_lower"], 
                right_on = ["state","congress","s_upper","s_lower"])

        # Filters elections by the race type requested
        relevant = relevant[relevant["race_type"] == layer]

        # Filters elections by voter power 
        relevant = relevant[relevant["voter_power_val"] > 10]
        # Sorts remaining elections by voter power & get only the top 3
        relevant.sort_values("voter_power_val", inplace = True, ascending = False)
        relevant.reset_index(drop = True)
        output = relevant[0:3]
        
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
        election_back = '<div class="col"><button type="button" class="btn btn-info">Get Involved</button></div></div></li>'
        item_front = '<div class="col">'
        item_back = '</div>'
        completed_string = ''
        statestr = "State: "
        vpstr = "Voter Power: "

        for i, election in election_list.iterrows():
            #logging.info(election)
            state_name = election["state"] + ", " + election["district_name"]
            election_vp = election["voter_power"]
            election_str = item_front + statestr + state_name + item_back + item_front + vpstr + election_vp + item_back
            completed_string = completed_string + election_front + election_str + election_back
        
        return completed_string