# This notebook imports ridership data and distributes the data to each subway line
# based on available capacity for each line at each complex (the level at which we get ridership data)


## Imports
import pandas as pd 
import requests
import os
import sys
# getting functions from the parent directory
library_path = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
if library_path not in sys.path:
    sys.path.append(library_path)

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
# Add the parent directory to sys.path
sys.path.append(parent_dir)
from functions import *
train_car_characteristics = pd.read_csv(f"{parent_dir}/saved_data/length_of_each_train.csv")
# removing late night and weekend special cases and entering in those values manually
train_car_characteristics = train_car_characteristics.drop_duplicates(subset='route_id', keep='first')

# data taken from 2024 average in O-D dataset (which is averaged over months....)
## API endpoint is too big for an internet data request
## https://data.ny.gov/Transportation/MTA-Subway-Origin-Destination-Ridership-Estimate-2/jsu2-fbtj/explore/query/SELECT%0A%20%20%60year%60%2C%0A%20%20%60day_of_week%60%2C%0A%20%20%60hour_of_day%60%2C%0A%20%20%60origin_station_complex_id%60%2C%0A%20%20sum%28%60estimated_average_ridership%60%29%20AS%20%60sum_estimated_average_ridership%60%0AGROUP%20BY%0A%20%20%60year%60%2C%0A%20%20%60day_of_week%60%2C%0A%20%20%60hour_of_day%60%2C%0A%20%20%60origin_station_complex_id%60%0AORDER%20BY%20%60sum_estimated_average_ridership%60%20DESC%20NULL%20LAST/page/aggregate

try:
    hourly_complex_ridership = pd.read_csv(f"{parent_dir}/saved_data/hourly_complex_ridership_od.csv")
    # data comes in as an average for a week over a month so dividing by the number of months to get average per week
    hourly_complex_ridership['Estimated Average Ridership'] = hourly_complex_ridership['Estimated Average Ridership'] / 12
    hourly_complex_ridership.columns = ['year', 'day_of_week_name', 'hour', 'complex_id', 'complex_name', 'average_ridership']
    print("Hourly ridership data loaded successfully.")
except Exception as e:
    print(e)

# Frequency Data
stops_w_service_frequencies = pd.read_csv(f"{parent_dir}/saved_data/stops_w_service_frequencies.csv", index_col=0)
## adding in capacity 
stops_w_service_frequencies = stops_w_service_frequencies.merge(train_car_characteristics, how='left', on='route_id')
for row in range(len(stops_w_service_frequencies)):
    if stops_w_service_frequencies.loc[row, 'hour'] < 6:
        if stops_w_service_frequencies.loc[row, 'route_id'] == 'M':
            stops_w_service_frequencies.loc[row, 'capacity'] = 992
        elif stops_w_service_frequencies.loc[row, 'route_id'] == '5':
            stops_w_service_frequencies.loc[row, 'capacity'] = 900
    elif stops_w_service_frequencies.loc[row, 'day_of_week'] != 'Weekday':
        if stops_w_service_frequencies.loc[row, 'route_id'] == 'M':
            stops_w_service_frequencies.loc[row, 'capacity'] = 992
stops_w_service_frequencies['frequency_capacity'] = stops_w_service_frequencies['frequency'] * stops_w_service_frequencies['capacity']

stations_df = pd.read_csv(f"{parent_dir}/data/MTA_Subway_Stations_20240325.csv")
stations_df = stations_df.drop(columns=['ADA', 'ADA Northbound', 'ADA Southbound'
                                        , 'ADA Notes', 'Georeference'])
station_count_df = pd.DataFrame(stations_df.groupby('Complex ID').count()['Station ID']).reset_index()
station_count_df.columns = ['Complex ID', 'stations_in_complex_count']
stations_df = stations_df.merge(station_count_df, how='left', on='Complex ID')
stations_df = stations_df[stations_df['Division']!='SIR']
# stations_df_w_complex_count = stations_df[['GTFS Stop ID', 'Complex ID', 'Line'
#                                            , 'Stop Name', 'stations_in_complex_count']]
# stations_df_w_complex_count.columns = ['stop_id', 'Complex ID', 'Line', 'Stop Name', 'stations_in_complex_count']
stations_df = stations_df[['GTFS Stop ID', 'Complex ID', 'Line', 'Stop Name']]
stations_df.columns = ['stop_id', 'Complex ID', 'Line', 'Stop Name']

complexes_by_dimensions = stops_w_service_frequencies.merge(stations_df, on='stop_id' )
complexes_w_frequency = complexes_by_dimensions.groupby(['Complex ID','day_of_week'
                                                         , 'hour', 'route_id']).sum()[['frequency', 'frequency_total', 'capacity'
                                                                                        , 'frequency_capacity']].reset_index()

# hourly_complex_ridership['departure_day'] = hourly_complex_ridership.departure_day.astype(str)
hourly_complex_ridership['day_of_week'] = hourly_complex_ridership['day_of_week_name'].replace({
                                            'Monday': 'Weekday', 'Tuesday': 'Weekday'
                                            , 'Wednesday': 'Weekday', 'Thursday': 'Weekday'
                                            , 'Friday': 'Weekday'
                                            , 'Saturday': 'Saturday', 'Sunday': 'Sunday'})
hourly_complex_ridership_day_type = pd.DataFrame(hourly_complex_ridership.groupby(['complex_id'
                                                                      , 'day_of_week'
                                                                      , 'hour']).sum()['average_ridership']).reset_index()
hourly_complex_ridership_day_type['average_ridership'] = [hourly_complex_ridership_day_type['average_ridership'][idx]/5 
                                                      if hourly_complex_ridership_day_type['day_of_week'][idx]=='Weekday'
                                                      else hourly_complex_ridership_day_type['average_ridership'][idx]
                                                      for idx in range(len(hourly_complex_ridership_day_type))]

complex_frequency_ridership = complexes_w_frequency.merge(hourly_complex_ridership_day_type
                                , left_on=['Complex ID', 'day_of_week', 'hour']
                                , right_on=['complex_id', 'day_of_week', 'hour'])
complex_frequency_ridership = complex_frequency_ridership.drop(columns=['complex_id'])
# Get frequency capacity by complex
complex_frequency_capacity = pd.DataFrame(complex_frequency_ridership.groupby(['Complex ID', 'day_of_week', 'hour'])['frequency_capacity'].sum()).reset_index()
complex_frequency_capacity.columns = ['Complex ID', 'day_of_week', 'hour', 'frequency_capacity_total']
complex_frequency_ridership = complex_frequency_ridership.merge(complex_frequency_capacity, how='left', on=['Complex ID', 'day_of_week', 'hour'])

# determine_train_time_intervals
complex_frequency_ridership['route_id_ridership'] = [complex_frequency_ridership['average_ridership'][idx] * 
                                                    (complex_frequency_ridership['frequency_capacity'][idx] 
                                                     / complex_frequency_ridership['frequency_capacity_total'][idx])
                                                    for idx in range(len(complex_frequency_ridership))]
# saving data to get day + hour ridership for each line
complex_frequency_ridership.to_csv(f"{parent_dir}/saved_data/routes_day_hour_station_ridership.csv")
day_hour_ridership = pd.DataFrame(complex_frequency_ridership.groupby(['route_id', 'day_of_week', 'hour'])['route_id_ridership'].sum())
day_hour_ridership.to_csv(f"{parent_dir}/saved_data/routes_day_hour_ridership.csv")

# re-transform single weekday to 5 days
route_id_ridership = complex_frequency_ridership.groupby(['route_id', 'day_of_week']).sum(['route_id_ridership']).reset_index()
route_id_ridership['weekday_ridership_adj'] = [route_id_ridership['route_id_ridership'][idx]*5 
                                                if route_id_ridership['day_of_week'][idx]=='Weekday'
                                                else route_id_ridership['route_id_ridership'][idx]
                                                for idx in range(len(route_id_ridership))]
route_id_ridership['frequency_capacity_adj'] = [route_id_ridership['frequency_capacity'][idx]*5 
                                                if route_id_ridership['day_of_week'][idx]=='Weekday'
                                                else route_id_ridership['frequency_capacity'][idx]
                                                for idx in range(len(route_id_ridership))]
route_id_ridership['daily_ridership_weekday'] = [route_id_ridership['route_id_ridership'][idx] 
                                                if route_id_ridership['day_of_week'][idx]=='Weekday'
                                                else 0
                                                for idx in range(len(route_id_ridership))]
route_id_ridership_grouped = pd.DataFrame(route_id_ridership.groupby('route_id').sum()[['weekday_ridership_adj', 'frequency_capacity_adj', 'daily_ridership_weekday']]).reset_index()
route_id_ridership_grouped['weekday_ridership_adj'] = (route_id_ridership_grouped['weekday_ridership_adj'] * 52.14)
route_id_ridership_grouped['crowdedness_linked'] = route_id_ridership_grouped['weekday_ridership_adj'] / route_id_ridership_grouped['frequency_capacity_adj'] 
route_id_ridership_grouped['weekday_ridership_adj'] = route_id_ridership_grouped['weekday_ridership_adj'] / 1000000
route_id_ridership_grouped['daily_ridership_weekday'] = route_id_ridership_grouped['daily_ridership_weekday'] / 1000
route_id_ridership_grouped.columns = ['route_id', 'yearly_ridership_MM', 'frequency_capacity', 'daily_ridership_weekday', 'crowdedness']
# including the average number of subway transfers for a more realistic estimate 
# (I found other ratios online) e.g.: 
#   - 1.49 (using values in this press release: https://www.governor.ny.gov/news/governor-hochul-highlights-record-breaking-year-performance-and-ridership-mta-2025)
#   - 1.84 (using 2024 total ridership and federal data on unlinked passenger trips: https://www.transit.dot.gov/sites/fta.dot.gov/files/transit_agency_profile_doc/2024/20008.pdf)
# source for unlinked passenger trips: https://en.wikipedia.org/wiki/New_York_City_Subway citing https://www.apta.com/wp-content/uploads/2024-Q4-Ridership-APTA.pdf (may include SIR which is ~5.6MM)
unlinked_trips_2024 = 2040132000
# source for linked passenger trips 2024: https://data.ny.gov/Transportation/MTA-Subway-Hourly-Ridership-2020-2024/wujg-7c2s/explore/query/SELECT%20%60transit_mode%60%2C%20sum%28%60ridership%60%29%20AS%20%60sum_ridership%60%0AWHERE%0A%20%20%60transit_timestamp%60%0A%20%20%20%20BETWEEN%20%222024-01-01T00%3A00%3A00%22%20%3A%3A%20floating_timestamp%0A%20%20%20%20AND%20%222025-01-01T00%3A00%3A00%22%20%3A%3A%20floating_timestamp%0AGROUP%20BY%20%60transit_mode%60%0AHAVING%20caseless_one_of%28%60transit_mode%60%2C%20%22subway%22%29/page/filter
linked_trips_2024 = 1206083955
services_per_linked_trip = unlinked_trips_2024 / linked_trips_2024
route_id_ridership_grouped['yearly_ridership_unlinked_MM'] = route_id_ridership_grouped['yearly_ridership_MM'] * services_per_linked_trip
# 2024 ridership (Q1 and Q2)
# https://data.ny.gov/Transportation/MTA-Subway-Hourly-Ridership-2020-2024/wujg-7c2s/explore/query/SELECT%20%60transit_mode%60%2C%20sum%28%60ridership%60%29%20AS%20%60sum_ridership%60%0AWHERE%0A%20%20%60transit_timestamp%60%0A%20%20%20%20BETWEEN%20%222024-01-01T00%3A00%3A00%22%20%3A%3A%20floating_timestamp%0A%20%20%20%20AND%20%222024-07-01T00%3A00%3A00%22%20%3A%3A%20floating_timestamp%0AGROUP%20BY%20%60transit_mode%60/page/aggregate
total_ridership_24 = 589117753
# 2025 ridership (Q1 and Q2)
# https://data.ny.gov/Transportation/MTA-Subway-Hourly-Ridership-Beginning-2025/5wq4-mkjj/explore/query/SELECT%20%60transit_mode%60%2C%20sum%28%60ridership%60%29%20AS%20%60sum_ridership%60%0AWHERE%0A%20%20%60transit_timestamp%60%0A%20%20%20%20BETWEEN%20%222025-01-01T00%3A00%3A00%22%20%3A%3A%20floating_timestamp%0A%20%20%20%20AND%20%222025-07-01T00%3A00%3A00%22%20%3A%3A%20floating_timestamp%0AGROUP%20BY%20%60transit_mode%60/page/aggregate
total_ridership_25 = 638233041
# 8% increase
yearly_change_ratio = total_ridership_25 / total_ridership_24
route_id_ridership_grouped['Adjusted_unlinked_2025'] = route_id_ridership_grouped['yearly_ridership_unlinked_MM'] * yearly_change_ratio
## rounding to thousands place
route_id_ridership_grouped['Adjusted_unlinked_2025_daily_thousands'] = route_id_ridership_grouped['daily_ridership_weekday'] * services_per_linked_trip * yearly_change_ratio
route_id_ridership_grouped['crowdedness_unlinked'] = (route_id_ridership_grouped['Adjusted_unlinked_2025'] * 1000000) / route_id_ridership_grouped['frequency_capacity']
route_id_ridership_grouped = round(route_id_ridership_grouped, 2)
route_id_ridership_grouped = route_id_ridership_grouped.sort_values(by='yearly_ridership_MM', ascending=False).reset_index(drop=True)

# Saving all Data 
if not os.path.exists(f'{parent_dir}/saved_data'):
    os.makedirs(f'{parent_dir}/saved_data')
route_id_ridership_grouped.to_csv(f"{parent_dir}/saved_data/routes_yearly_ridership.csv")
route_id_ridership_grouped.to_csv(f"{parent_dir}/Outputs/routes_yearly_ridership.csv")
