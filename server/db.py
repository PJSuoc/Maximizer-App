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
        self.elections = pd.read_csv("./static/data/distric_races_by_county.csv")


    def nearby_voting_impact(self, location):
        '''
        Function set for getting 
        '''
        nearby_shapes = self.shapes_near_location(location)
        near_close_elections = self.competitive_races(nearby_shapes)
        clean_output = self.output_formatter(near_close_elections)
        return clean_output
    
    def shapes_near_location(self, location):
        shape = self.congress # Temporary, in the future will be the mergeset of shapes
        lat = location[0]["geometry"]["location"]["lat"]
        lng = location[0]["geometry"]["location"]["lng"]
        location = Point((lng,lat))
        loc_df = gpd.GeoDataFrame(geometry=[location], crs=4269)
        loc_df = loc_df.to_crs(3857)
        loc_range = loc_df.buffer(160000) #80k meters is approx. 50 miles
        loc_range = loc_range.to_crs(4269)
        shape["close"] = shape.intersects(loc_range[0])
        return shape[shape["close"]==True]

    def competitive_races(self, shapelist):
        self.elections["STATEFP"] = self.elections["STATEFP"].astype("str")
        self.elections["NAMELSAD"] = self.elections["NAMELSAD"].astype("str")
        self.elections["NAMELSAD"] = self.elections["NAMELSAD"].str.zfill(2)
        compdist = shapelist.merge(self.elections, how="inner", \
            left_on =["STATEFP", "CD118FP"], right_on = ["STATEFP", "NAMELSAD"])
        return compdist
    
    def output_formatter(self, list):
        removed_extras = list[["state","CD118FP","Incumbent affiliation", "Leans"]]
        return removed_extras