from os import path
import logging
import sqlite3 as sqlite
import pandas as pd
import geopandas as gpd

"""
Class for building database functionalities.
"""
class DB:
    def __init__(self, connection):
        self.conn = connection
        # There are 4 initial layers of shapes:
        # 1. State shapes
        # 2. Congressional District Shapes
        # 3. State Legislature Shapes [1] (State House, typically)
        # 4. State Legislature Shapes [2] (Senate Senate, typically)

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
        self.states = gpd.read_file("data\cb_2023_us_cd118_500k.shp")
        self.elections = pd.read_csv("data\distric_races_by_county.csv")

    def shapes_near_location(self, location):
        range_series = location.buffer(80000) #80k meters is approx. 50 miles
        x = self.states.overlaps(range_series)
        
