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
    print("Data already saved in local directory.")
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

# Frequency Data
stops_w_service_frequencies = pd.read_csv(f"{parent_dir}/saved_data/stops_w_service_frequencies.csv", index_col=0)

stations_df = pd.read_csv(f"{parent_dir}/data/MTA_Subway_Stations_20240325.csv")
stations_df = stations_df.drop(columns=['ADA', 'ADA Northbound', 'ADA Southbound'
                                        , 'ADA Notes', 'Georeference'])
station_count_df = pd.DataFrame(stations_df.groupby('Complex ID').count()['Station ID']).reset_index()
station_count_df.columns = ['Complex ID', 'stations_in_complex_count']
stations_df = stations_df.merge(station_count_df, how='left', on='Complex ID')
stations_df = stations_df[stations_df['Division']!='SIR']
stations_df_w_complex_count = stations_df[['GTFS Stop ID', 'Complex ID', 'Line'
                                           , 'Stop Name', 'stations_in_complex_count']]
stations_df_w_complex_count.columns = ['stop_id', 'Complex ID', 'Line', 'Stop Name', 'stations_in_complex_count']
stations_df = stations_df[['GTFS Stop ID', 'Complex ID', 'Line', 'Stop Name']]
stations_df.columns = ['stop_id', 'Complex ID', 'Line', 'Stop Name']

complexes_by_dimensions = stops_w_service_frequencies.merge(stations_df, on='stop_id' )
complexes_w_frequency = complexes_by_dimensions.groupby(['Complex ID', 'stop_id',
                                                          'day_of_week', 'hour', 'route_id']).sum()[['frequency', 'frequency_total']].reset_index()
# data taken from one week in the summer of 2024. It's eventually scaled to a year
hourly_station_ridership['departure_day'] = hourly_station_ridership.departure_day.astype(str)
hourly_station_ridership['day_of_week'] = hourly_station_ridership['departure_day'].replace({
                                            '0': 'Weekday', '1': 'Weekday', '2': 'Weekday'
                                            , '3': 'Weekday', '4': 'Weekday'
                                            , '5': 'Saturday', '6': 'Sunday'})
hourly_station_ridership_day_type = pd.DataFrame(hourly_station_ridership.groupby(['station_complex_id'
                                                                      , 'day_of_week'
                                                                      , 'departure_hour']).sum()['sum_ridership']).reset_index()
hourly_station_ridership_day_type['sum_ridership'] = [hourly_station_ridership_day_type['sum_ridership'][idx]/5 
                                                      if hourly_station_ridership_day_type['day_of_week'][idx]=='Weekday'
                                                      else hourly_station_ridership_day_type['sum_ridership'][idx]
                                                      for idx in range(len(hourly_station_ridership_day_type))]

complex_frequency_ridership = complexes_w_frequency.merge(hourly_station_ridership_day_type
                                , left_on=['Complex ID', 'day_of_week', 'hour']
                                , right_on=['station_complex_id', 'day_of_week', 'departure_hour'])
complex_frequency_ridership = complex_frequency_ridership.drop(columns=['station_complex_id'
                                                                        , 'departure_hour'])
complex_frequency_ridership['route_id_ridership'] = [complex_frequency_ridership['sum_ridership'][idx] * 
                                                    (complex_frequency_ridership['frequency'][idx] / complex_frequency_ridership['frequency_total'][idx])
                                                    for idx in range(len(complex_frequency_ridership))]
route_id_ridership = complex_frequency_ridership.groupby(['route_id'
                                                          , 'day_of_week']).sum(['route_id_ridership']).reset_index()
route_id_ridership['weekday_ridership_adj'] = [route_id_ridership['route_id_ridership'][idx]*5 
                                                if route_id_ridership['day_of_week'][idx]=='Weekday'
                                                else route_id_ridership['route_id_ridership'][idx]
                                                for idx in range(len(route_id_ridership))]
route_id_ridership_grouped = pd.DataFrame(route_id_ridership.groupby('route_id').sum()['weekday_ridership_adj']).reset_index()
route_id_ridership_grouped['weekday_ridership_adj'] = route_id_ridership_grouped['weekday_ridership_adj'] * 52.14
route_id_ridership_grouped.columns = ['route_id', 'yearly_ridership']

# next step is to take into account train area (mostly because the Grand Central Shuttle is suspect)
route_id_ridership_grouped = route_id_ridership_grouped.sort_values(by='yearly_ridership', ascending=False)













# Saving all Data 
if not os.path.exists(f'{parent_dir}/saved_data'):
    os.makedirs(f'{parent_dir}/saved_data')

route_id_ridership_grouped.to_csv(f"{parent_dir}/saved_data/routes_yearly_ridership.csv")