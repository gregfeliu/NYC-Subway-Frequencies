# Creating Station Information

## Imports
import pandas as pd 
import os
import numpy as np
import datetime
from functions import *

### Importing Data
# https://data.ny.gov/Transportation/MTA-Subway-Stations-Map/p6ps-59h2
stations_df = pd.read_csv("data/MTA_Subway_Stations_20240325.csv")
stations_df = stations_df.drop(columns=['ADA', 'ADA Northbound', 'ADA Southbound'
                                        , 'ADA Notes', 'Georeference'])
station_count_df = pd.DataFrame(stations_df.groupby('Complex ID').count()['Station ID']).reset_index()
station_count_df.columns = ['Complex ID', 'stations_in_complex_count']
stations_df = stations_df.merge(station_count_df, how='left', on='Complex ID')

stop_times_df = pd.read_csv("data/google_transit/stop_times.txt")
train_area_df = pd.read_csv("saved_data/length_of_each_train.csv", index_col=0)

## Data Adjustments
stop_times_df['departure_time']  = [str(int(x[0:2]) - 24) + x[2:] if int(x[0:2]) >= 24 else x
                                    for x in stop_times_df['departure_time']]
stop_times_df['departure_time'] = pd.to_datetime(stop_times_df['departure_time'], format="%H:%M:%S", errors='coerce')
stop_times_df = group_into_day_type(stop_times_df, 'trip_id')

# Creating Station Information
stop_times_df['route_id'] = [x.split("_")[-1].split('.')[0] 
                                        for x in stop_times_df['trip_id']]
stop_times_df['parent_stop_id'] = [x[0:-1] for x in stop_times_df['stop_id']]
stop_times_df['hour'] = [x.hour for x in stop_times_df['departure_time']]

train_time_interval_list = []
for idx, row in stop_times_df.iterrows():
    train_time_interval = determine_train_time_intervals(row['departure_time'], row['day_of_week'])
    train_time_interval_list.append(train_time_interval)
stop_times_df['train_time_interval'] = train_time_interval_list

train_area_dict = dict(zip(train_area_df.route_id, train_area_df['trainset_area']))
stop_times_df['trainset_area'] = stop_times_df['route_id'].replace(train_area_dict)

# trains per hour during non-late nights
# this includes both directions so I'm dividing by 2 to make it "per direction"
# dividing by 7 to get single day and dividing by 18 non-late night hours
non_late_night_stop_times_df = stop_times_df[stop_times_df['train_time_interval']!='Late Night']

non_late_night_full_schedule = upsample_weekday_values(non_late_night_stop_times_df[['trip_id', 'parent_stop_id', 'day_of_week', 'trainset_area'
                                                                                     , 'train_time_interval']], 'day_of_week')
trains_per_waking_hour_by_station = round(non_late_night_full_schedule.groupby('parent_stop_id').count() / 18 / 7 / 2, 2)[['trip_id']]
trains_per_waking_hour_by_station.reset_index(inplace=True)
# train area per hour during weekdays per direction
train_area_per_waking_hour_by_station = round(non_late_night_full_schedule.groupby('parent_stop_id').sum() / 18 / 7 / 2, 2)[['trainset_area']]
train_area_per_waking_hour_by_station.reset_index(inplace=True)
train_info_per_waking_hour_by_station = pd.merge(trains_per_waking_hour_by_station
                                                  , train_area_per_waking_hour_by_station)
train_info_per_waking_hour_by_station.columns = ['parent_stop_id', 'trains_per_hour', 'hourly_trainset_area']
train_info_per_waking_hour_by_station['capacity'] = round(train_info_per_waking_hour_by_station['hourly_trainset_area'] / 4.2, 1)
train_info_per_waking_hour_by_station['mean_wait_time'] = round(60 / \
                                                            train_info_per_waking_hour_by_station['trains_per_hour'], 1)

station_info_w_frequency = stations_df.merge(train_info_per_waking_hour_by_station, how='outer',
                                                    left_on='GTFS Stop ID', right_on='parent_stop_id')
station_info_w_frequency = station_info_w_frequency.drop(columns=['parent_stop_id', 'Station ID'
                                                                  , 'GTFS Latitude', 'GTFS Longitude'
                                                                  , 'North Direction Label', 'South Direction Label'])
## Making a wide df that shows tph for all time intervals for each station
for idx, interval in enumerate(stop_times_df['train_time_interval'].unique()):
    # some late night service will be null (since it went over 24 hours)
    if interval:
        station_frequency_interval_df = stop_times_df[stop_times_df['train_time_interval']==interval
                                                    ].groupby('parent_stop_id').count()[['trip_id']]
        station_frequency_interval_df.reset_index(inplace=True)
        station_frequency_interval_df.columns = ['parent_stop_id', 'trains_per_hour']
        # getting the data to be "per direction"
        station_frequency_interval_df['trains_per_hour'] = station_frequency_interval_df['trains_per_hour'] / 2
        station_frequency_interval_df['train_time_interval'] = interval
        station_frequency_interval_df = scale_time_intervals_to_hour(station_frequency_interval_df)
        station_frequency_interval_df = station_frequency_interval_df.round(1)
        station_frequency_interval_df = station_frequency_interval_df.drop(columns=['train_time_interval'])
        station_frequency_interval_df.columns=['parent_stop_id', interval]
        # adding to total dataframe
        station_info_w_frequency = station_info_w_frequency.merge(station_frequency_interval_df
                                        , how='left', left_on='GTFS Stop ID', right_on='parent_stop_id')
        # station_info_w_frequency.drop(columns=['parent_stop_id_x', 'parent_stop_id_y'], inplace=True)
station_info_w_frequency.drop(columns=[col for col in station_info_w_frequency.columns 
                                       if 'parent_stop_id' in col], axis=1, inplace=True)

# Saving the Data 
if not os.path.exists('saved_data'):
    os.makedirs('saved_data')
stations_df.to_csv("saved_data/stations_df.csv")
station_info_w_frequency.to_csv('saved_data/station_info_w_frequency.csv')