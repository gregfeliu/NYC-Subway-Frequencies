# Creating Streamlit app
## Imports
import pandas as pd 
import os
import sys
import numpy as np
# getting functions from the parent directory
library_path = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
if library_path not in sys.path:
    sys.path.append(library_path)
from functions import *




# data 
### hourly
hourly_route_trip_freq = pd.read_csv("../data/hourly_route_trip_freq.csv", index_col=0)
hourly_route_trip_freq = hourly_route_trip_freq[hourly_route_trip_freq['route_id']!='SI']
hourly_route_trip_freq = hourly_route_trip_freq.drop(columns=['route_time_seconds'
                                                            , 'Avg_num_trains_running'
                                                            , 'headway_seconds'
                                                            , 'route_time_minutes'])
hourly_route_trip_freq = hourly_route_trip_freq.round()
hourly_route_trip_freq.columns = ['Service', 'Day of Week', 'Hour', 'Trains per Hour (Each Direction)', 'Average Wait Time (Minutes)']
hourly_route_trip_freq = hourly_route_trip_freq.set_index("Service")
### daily
daily_route_trip_freq = hourly_route_trip_freq.drop(columns=['Hour'])
daily_route_trip_freq = daily_route_trip_freq.groupby(['Service', 'Day of Week']).sum() / 24
daily_route_trip_freq = daily_route_trip_freq.round()
## train time interval
trip_interval_route_freq = pd.read_csv("../data/trip_interval_route_freq.csv", index_col=0)
trip_interval_route_freq = trip_interval_route_freq[trip_interval_route_freq['route_id']!='SI']
trip_interval_route_freq = trip_interval_route_freq.drop(columns=['route_time_seconds'
                                                            , 'Avg_num_trains_running'
                                                            , 'headway_seconds'
                                                            , 'route_time_minutes'])
# add custom time period ordering 
trip_interval_route_freq = trip_interval_route_freq.round()
trip_interval_route_freq.columns = ['Service', 'Time Interval', 'Trains per Hour (Each Direction)', 'Average Wait Time (Minutes)']
trip_interval_route_freq = trip_interval_route_freq.set_index("Service")
trip_interval_route_freq = trip_interval_route_freq.round()

# # Line, Complex, Station Data 
# station_info_w_frequency = pd.read_csv("../data/station_info_w_frequency.csv", index_col=0)
# station_info_w_frequency = station_info_w_frequency[station_info_w_frequency['Borough']!='SI']
# station_info_w_frequency = station_info_w_frequency.drop(columns=['Daytime Routes', 'Structure', 
#                                                                   'stations_in_complex_count'
#                                                                   , 'hourly_trainset_area', 'mean_wait_time'])
# # hourly ridership/frequency by complex 
# ## Getting Hourly tph for each hour and station 
# hourly_station_tph = pd.read_csv("../data/hourly_station_tph.csv", index_col=0)
# hourly_station_tph = hourly_station_tph[~hourly_station_tph['parent_stop_id'].str.contains('S')]
# hourly_station_tph.columns = ['Station ID', 'Day of Week', 'Hour', 'TPH']
# # add the stop name, complex id, line to this data 

# Saving all Data 
if not os.path.exists('data'):
    os.makedirs('data')

hourly_route_trip_freq.to_csv("../data/hourly_route_trip_freq.csv")
daily_route_trip_freq.to_csv("../data/daily_route_trip_freq.csv")
trip_interval_route_freq.to_csv("../data/trip_interval_route_freq.csv")