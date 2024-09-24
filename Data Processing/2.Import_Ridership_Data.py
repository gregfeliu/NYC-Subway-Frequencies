# Importing Ridership Data 

## Imports
import pandas as pd 
import requests
import os
import sys
# getting functions from the parent directory
library_path = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
if library_path not in sys.path:
    sys.path.append(library_path)
# from functions import *

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
# Add the parent directory to sys.path
sys.path.append(parent_dir)
from functions import *

# Only making an api call if we don't already have the hourly station ridership data 
try:
    hourly_station_ridership = pd.read_csv(f"{parent_dir}/saved_data/hourly_station_ridership.csv", index_col=0)
except Exception as e:
    copied_url = "https://data.ny.gov/resource/wujg-7c2s.json?$limit=1000000&$where=transit_timestamp >= '2024-06-24T00:00:00' AND transit_timestamp <= '2024-06-30T23:59:59' AND transit_mode = 'subway'&$order=transit_timestamp ASC&$group=transit_timestamp, station_complex_id&$select=transit_timestamp, station_complex_id, sum(ridership) as sum_ridership"
    response = requests.get(copied_url)
    response_data = response.json()
    hourly_station_ridership = pd.DataFrame(response_data)
    hourly_station_ridership['time_as_datetime'] = pd.to_datetime(hourly_station_ridership['transit_timestamp']
                                                              , errors='coerce')
    hourly_station_ridership['station_complex_id'] = hourly_station_ridership['station_complex_id'].astype(float)
    hourly_station_ridership['sum_ridership'] = hourly_station_ridership['sum_ridership'].astype(float)
    # adding the time data 
    hourly_station_ridership['departure_hour'] = hourly_station_ridership['time_as_datetime'].dt.hour
    hourly_station_ridership['departure_day'] = hourly_station_ridership['time_as_datetime'].dt.weekday
    hourly_station_ridership.drop(columns=['transit_timestamp'], inplace=True)
    if not os.path.exists(f'{parent_dir}/saved_data'):
        os.makedirs(f'{parent_dir}/saved_data')
    hourly_station_ridership.to_csv(f"{parent_dir}/saved_data/hourly_station_ridership.csv")