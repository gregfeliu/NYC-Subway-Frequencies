# Schedule Data 
## Outputs:
##         - All trips in the schedule  
##         - Info about all Service s 
##         - Hourly Frequencies 
##         - Train Time Interval Frequencies 

## Imports
import pandas as pd 
import numpy as np
import sys
import os

# Get the current file's directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
# Add the parent directory to sys.path
sys.path.append(parent_dir)
from functions import *

### Data 
stop_times_df = pd.read_csv(f"{parent_dir}/data/google_transit/stop_times.txt")
stops_df = pd.read_csv(f"{parent_dir}/data/google_transit/stops.txt")
trips_df = pd.read_csv(f"{parent_dir}/data/google_transit/trips.txt")

# Adjusting the data
### finding all non-standard trips to remove later
non_standard_trips = trips_df[~trips_df['service_id'].isin(['Weekday', 'Saturday', 'Sunday'])]
# G, J/Z are having service changes
print(f'The services {non_standard_trips['route_id'].unique()} are having long term service changes')

### making the times within a 24 hour range -- originally is up to 27 
stop_times_df['departure_time'] = [str(int(x[0:2]) - 24) + x[2:] if int(x[0:2]) >= 24 else x
                                    for x in stop_times_df['departure_time']]
# converting to a datetime
stop_times_df['departure_time'] = pd.to_datetime(stop_times_df['departure_time'], format="%H:%M:%S", errors='coerce')
stop_times_df = group_into_day_type(stop_times_df, 'trip_id')
stop_times_df = stop_times_df.drop(columns=['stop_id', 'arrival_time'])
stop_times_df = stop_times_df[~stop_times_df['departure_time'].isnull()]
stop_times_df = stop_times_df[~stop_times_df['trip_id'].isin(non_standard_trips['trip_id'])]

# All Trips
first_stop_in_trip = stop_times_df[stop_times_df['stop_sequence']==1]
first_stop_in_trip = first_stop_in_trip.drop(columns=['stop_sequence'])
first_stop_in_trip['departure_hour'] = first_stop_in_trip['departure_time'].dt.hour
first_stop_in_trip['route_id'] = [x.split("_")[-1].split('.')[0] 
                                        for x in first_stop_in_trip['trip_id']]
first_stop_in_trip['shape_id'] = [x.split("_")[-1] for x in first_stop_in_trip['trip_id']]
first_stop_in_trip = first_stop_in_trip[~first_stop_in_trip.departure_time.isnull()]

## Making the data be "per direction" (closer to how an average person would think interpret this)
## the shuttles only have 1 "." -- very close to 50:50 (50.6 ~ 49.4)
directions = []
for x in first_stop_in_trip['shape_id']:
    direction = x.split(".", 1)[1]
    if "S" in direction:
        directions.append("S")
    else:
        directions.append("N")
first_stop_in_trip['direction'] = directions
first_stop_in_trip = first_stop_in_trip[first_stop_in_trip['direction'] == 'S']

## Adding Train Time Interval Categorization 
train_time_interval_list = []
for idx, row in first_stop_in_trip.iterrows():
    train_time_interval = determine_train_time_intervals(row['departure_time'], row['day_of_week'])
    train_time_interval_list.append(train_time_interval)
first_stop_in_trip['train_time_interval'] = train_time_interval_list

# Info about each Service
# calculating the raw hour:minute:second values because the time going above 24 hours is difficult to deal with
stop_times_df = pd.read_csv(f"{parent_dir}/data/google_transit/stop_times.txt")
str_departure_time = [str_time_to_minutes(x) for x in stop_times_df['departure_time']]
stop_times_df['str_departure_time'] = str_departure_time
trip_time_diff = stop_times_df.groupby('trip_id')['str_departure_time'].agg(np.ptp)
valid_trip_times = pd.DataFrame(trip_time_diff).reset_index()
valid_trip_times['route_id'] = [x.split("_")[-1].split('.')[0] 
                                        for x in valid_trip_times['trip_id']]
# Average trip time for each service
avg_trip_time = pd.DataFrame(valid_trip_times.groupby('route_id')['str_departure_time'].mean()).reset_index()
avg_trip_time['route_time_seconds'] = [round(x * 60) for x in avg_trip_time['str_departure_time']]
avg_trip_time['route_time_minutes'] = [round(x, 1) for x in avg_trip_time['str_departure_time']]
# the amount of time it takes to reach one end of the route from the other
avg_trip_time_final = avg_trip_time.drop(columns='str_departure_time')


# Hourly 
route_trip_freq_by_hour = first_stop_in_trip.groupby(['route_id', 'day_of_week', 'departure_hour'])[['trip_id']].count()
route_trip_freq_by_hour.columns = ['trains_per_hour']
route_trip_freq_by_hour['headway_seconds'] = round(3600 / route_trip_freq_by_hour['trains_per_hour'])
route_trip_freq_by_hour['headway_minutes'] = round(60 / route_trip_freq_by_hour['trains_per_hour'], 1)
hourly_route_trip_freq = route_trip_freq_by_hour.reset_index().merge(avg_trip_time_final, on='route_id')
# doubling the result so that we have ALL trains not just southbound ones
hourly_route_trip_freq['Avg_num_trains_running'] = (hourly_route_trip_freq['route_time_minutes'] / 60) * \
                                        hourly_route_trip_freq['trains_per_hour'] * 2
hourly_route_trip_freq = hourly_route_trip_freq.round(1)

# Train Time Interval
first_stop_in_trip_per_interval = pd.DataFrame(first_stop_in_trip.groupby(
                                                ['route_id', 'train_time_interval']
                                                ).size()).reset_index()
first_stop_in_trip_per_interval.columns = ['route_id', 'train_time_interval', 'trains_per_hour']
first_stop_in_trip_per_interval = scale_time_intervals_to_hour(first_stop_in_trip_per_interval)
first_stop_in_trip_per_interval['headway_seconds'] = round(3600 / first_stop_in_trip_per_interval['trains_per_hour'])
first_stop_in_trip_per_interval['headway_minutes'] = round(60 / first_stop_in_trip_per_interval['trains_per_hour'], 1)
trip_interval_route_freq = first_stop_in_trip_per_interval.merge(avg_trip_time_final, on='route_id')

# doubling the result so that we have ALL trains not just southbound ones
trip_interval_route_freq['Avg_num_trains_running'] = (trip_interval_route_freq['route_time_minutes'] / 60) * \
                                        trip_interval_route_freq['trains_per_hour'] * 2
trip_interval_route_freq = trip_interval_route_freq.round(1)

# Daily / Overall
route_frequency_by_day = pd.DataFrame(first_stop_in_trip.groupby(
                                                ['route_id', 'day_of_week']).size() / 24).reset_index()
route_frequency_by_day.columns = ['route_id', 'day_of_week', 'trains_per_hour']
route_frequency_by_day['headway_seconds'] = 3600 / route_frequency_by_day['trains_per_hour']
route_frequency_by_day['headway_minutes'] = 60 / route_frequency_by_day['trains_per_hour']
route_frequency_by_day = route_frequency_by_day.round(1)
# route_trip_freq_by_day = route_trip_freq_by_hour.groupby(['route_id']).sum() / 24
# # upsampling the weekday data 
# route_trip_freq_by_day.columns = ['Saturday', 'Sunday', 'Weekday'
#                                           , 'Weekday_Adjusted', 'Trains_per_Hour_Overall']
# # the wait time is half of the mean time between trains
# route_trip_freq_by_day['Headway_Minutes'] = 60 / route_trip_freq_by_day['Trains_per_Hour_Overall']
# route_trip_freq_by_day = route_trip_freq_by_day.round(1)
# daily_route_trip_freq = route_trip_freq_by_day.merge(avg_trip_time_final, on='route_id')
# # doubling the result so that we have ALL trains not just southbound ones
# daily_route_trip_freq['Avg_num_trains_running'] = round((daily_route_trip_freq['route_time_minutes'] / 60) * \
#                                                         daily_route_trip_freq['Trains_per_Hour_Overall'] * 2, 1)


# Saving all Data 
if not os.path.exists('../saved_data'):
    os.makedirs('../saved_data')

first_stop_in_trip.to_csv(f"{parent_dir}/saved_data/first_stop_in_trip.csv")
avg_trip_time_final.to_csv(f"{parent_dir}/saved_data/average_trip_time_per_service.csv")
hourly_route_trip_freq.to_csv(f"{parent_dir}/saved_data/hourly_route_trip_freq.csv")
trip_interval_route_freq.to_csv(f"{parent_dir}/saved_data/trip_interval_route_freq.csv")
route_frequency_by_day.to_csv(f"{parent_dir}/saved_data/route_frequency_by_day.csv")
