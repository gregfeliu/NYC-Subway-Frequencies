# Schedule Data 
## Outputs:
##         - All trips in the schedule  
##         - Info about all Services 
##         - Hourly frequencies by station, service, day and hour
##         - Train time interval frequencies by station and service

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
trips_df = pd.read_csv(f"{parent_dir}/data/google_transit/trips.txt")

# Adjusting the data
### finding all non-standard trips to remove later
non_standard_trips = trips_df[trips_df['service_id'].str.contains('-1')]
# G, J/Z were having service changes
print(f'The services {non_standard_trips['route_id'].unique()} are having long term service changes')

### making the times within a 24 hour range -- originally is up to 27 
stop_times_df['departure_time'] = [str(int(x[0:2]) - 24) + x[2:] if int(x[0:2]) >= 24 else x
                                    for x in stop_times_df['departure_time']]
# converting to a datetime
stop_times_df['departure_time'] = pd.to_datetime(stop_times_df['departure_time'], format="%H:%M:%S", errors='coerce')
stop_times_df = group_into_day_type(stop_times_df, 'trip_id')
stop_times_df = stop_times_df.drop(columns=['arrival_time'])
stop_times_df = stop_times_df[~stop_times_df['departure_time'].isnull()]
# removes 0.2% of all trip ids
stop_times_df = stop_times_df[~stop_times_df['trip_id'].isin(non_standard_trips['trip_id'])]


## remove the last stop for a trip 
# this is b/c we're counting the services people are CONTINUING to after entering a station

# Trips without a final stop
max_trip_ids = pd.DataFrame(stop_times_df.groupby('trip_id').max('stop_sequence')['stop_sequence'])
stop_times_df = stop_times_df.join(max_trip_ids, on='trip_id', rsuffix='_max')
stops_no_final_station = stop_times_df[stop_times_df['stop_sequence']!=stop_times_df['stop_sequence_max']]
stops_no_final_station['departure_hour'] = stops_no_final_station['departure_time'].dt.hour

stops_no_final_station['route_id'] = [x.split("_")[-1].split('.')[0] 
                                        for x in stops_no_final_station['trip_id']]
# stops_no_final_station['shape_id'] = [x.split("_")[-1] for x in stops_no_final_station['trip_id']]
# excluding SIR since this one is very straightforward to estimate 
stops_no_final_station = stops_no_final_station[stops_no_final_station['route_id']!='SI']
stops_no_final_station = stops_no_final_station[~stops_no_final_station.departure_time.isnull()]
stops_no_final_station = stops_no_final_station.drop(columns=['departure_time', 'stop_sequence', 'stop_sequence_max'])
stops_no_final_station['stop_id'] = [x[0:-1] for x in stops_no_final_station['stop_id']]
# stops by station, day, hour, and route
stops_by_dimensions = pd.DataFrame(stops_no_final_station.groupby(['stop_id', 'day_of_week', 'departure_hour', 'route_id']).count())
stops_by_dimensions = stops_by_dimensions.reset_index()
stops_by_dimensions.columns=['stop_id', 'day_of_week', 'hour', 'route_id', 'frequency']
stop_by_dimensions_totals = stops_by_dimensions.groupby(['stop_id', 'day_of_week', 'hour']).sum(['frequency'])
stops_by_dimensions_final = stops_by_dimensions.join(stop_by_dimensions_totals, on=['stop_id', 'day_of_week', 'hour'], rsuffix='_total')

# Saving all Data 
if not os.path.exists(f'{parent_dir}/saved_data'):
    os.makedirs(f'{parent_dir}/saved_data')

stops_by_dimensions_final.to_csv(f"{parent_dir}/saved_data/stops_w_service_frequencies.csv")
