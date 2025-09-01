# Creating Car Characteristics/Details

## Imports
import pandas as pd 
import os
import sys
import numpy as np

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
# Add the parent directory to sys.path
sys.path.append(parent_dir)
from functions import *


### Data Imports
first_stop_in_trip = pd.read_csv(f"{parent_dir}/saved_data/first_stop_in_trip.csv", index_col=0)

# a dictionary showing the length of each car for each line 
# source: https://en.wikipedia.org/wiki/New_York_City_Subway_rolling_stock
typical_length_of_cars = {'A': 15.5, 'B1': 18.4, 'B2':23}
typical_width_of_cars = {'A': 2.7, 'B': 3.1}

unique_lines = list(first_stop_in_trip.route_id.unique())
division_split_dict = dict(zip(unique_lines
                             , [None for x in range(len(unique_lines))]))
for key, value in division_split_dict.items():
    try:
        if key == 'GS':
            division_split_dict[key] = 'A'
        elif int(key[0]):
            division_split_dict[key] = 'A'
    except Exception as e:
        division_split_dict[key] = 'B'

train_area_df = pd.DataFrame.from_dict(division_split_dict, orient='index', columns=['division']).reset_index()
train_area_df.columns = ['route_id', 'division']

# Info about the Car Lengths for B Division Services:
# - According to the [latest track assignments](https://erausa.org/pdf/bulletin/2020s/2024/2024-02-bulletin.pdf) (Dec. 28) and Wikipedia's information about the [NYC Rolling Stock](https://en.wikipedia.org/wiki/New_York_City_Subway_rolling_stock#Current_fleet), here's the B1 and B2 breakdown of B-division cars in IND/BMT Routes:
#     - Because of track geometry and station lengths, the J, L, M, Z lines *must* use the 60 foot cars
#     - The B, D, N, Q, FS, and SI *exclusively* use the 75 foot cars (although this is evolving)
#     - The A, C (was [introduced in 2017](https://www.amny.com/transit/c-train-longer-cars-1-15512261/) 
#           for this line), and H use a mix of 60 foot and 75 car train sets
#     - The other lines *could* use 75 foot cars but currently only use 60 foot cars

# giving all car lengths by service 
# Some complications to this summarized here: https://www.etany.org/statements/impeding-progress-costing-riders-opto 
# we'll multiply their value by the number of cars to get the final length
car_length_dict = division_split_dict.copy()
b_div_services_75 = ['B', 'D', 'N', 'FS', 'SI', 'W']
bmt_eastern_division = ['J', 'Z', 'L', 'M']
for key, value in car_length_dict.items():
    if value == 'A':
        car_length_dict[key] = typical_length_of_cars[value]
    elif key in b_div_services_75:
        car_length_dict[key] = typical_length_of_cars['B2']
# undercounting the true capacity (it's not clear how often 75 foot car train sets are used)
# not sure if I'm undercounting because the number of cars/length of cars both equal 
# 600 ft of car length of trainset
    else:
        car_length_dict[key] = typical_length_of_cars['B1']
train_area_df['car_length'] = car_length_dict.values()
train_area_df['car_width'] = [typical_width_of_cars[x] for x in train_area_df['division']]

cars_per_train_dict = dict(zip(unique_lines, [None for x in range(len(unique_lines))]))
# B1 division
for service in ['C'] + b_div_services_75 + bmt_eastern_division:
    cars_per_train_dict[service] = 8
# I can't determine which one is used from the GTFS data
# Shuttles
cars_per_train_dict['FS'] = 2
cars_per_train_dict['H'] = 5
cars_per_train_dict['GS'] = 6
# Other
cars_per_train_dict['SI'] = 4
# this is changing slightly as the R211T trains are inserted into service (20% more capacity because of fewer seats)
cars_per_train_dict['G'] = 5
cars_per_train_dict['7'] = 11
cars_per_train_dict['7X'] = 11

train_area_df['number_of_cars'] = train_area_df['route_id'].replace(cars_per_train_dict)
for idx in range(len(train_area_df)):
    value = train_area_df['number_of_cars'][idx]
    if pd.isnull(value):
        if train_area_df['division'][idx] == 'A':
            value = 10
        elif train_area_df['division'][idx] == 'B':
            value = 10
    train_area_df['number_of_cars'][idx] = value

# all car capacities are around 4.3 people per sq meter 
# this isn't including seats vs. standing though so standees will have less space than that
# train_area_df['people_per_sq_meter'] = train_area_df['capacity'] / train_area_df['trainset_area']

# capacity of A div (e.g.: R142) ~ 180, B1 div (R160A) ~240, B2 (scaled from B1 div) = 300
# GS doesn't have seats which slightly increases capacity
train_area_df['train_length'] = train_area_df['car_length'] * train_area_df['number_of_cars']
train_area_df['trainset_area'] = round(train_area_df['train_length'] * train_area_df['car_width'])
train_area_dict = dict(zip(train_area_df.route_id, train_area_df['trainset_area']))
capacity_per_car = []
# getting capacity from this MTA source (for rush hour): ## updated to use MTA official time periods: https://www.mta.info/document/152001
for x in range(train_area_df.shape[0]):
    if train_area_df['car_length'][x] == 15.5:
        capacity_per_car.append(180)
    elif train_area_df['car_length'][x] == 18.4:
        capacity_per_car.append(248)  # very similar number for R211
    elif train_area_df['car_length'][x] == 23:
        capacity_per_car.append(278)  
train_area_df['capacity_per_car'] = capacity_per_car
train_area_df['capacity'] = [int(train_area_df['number_of_cars'][x] * train_area_df['capacity_per_car'][x])
                             for x in range(train_area_df.shape[0])]

# The 5, M, and Lefferts Blvd Shuttle (A) are all slightly shorter at late nights and weekends (ignoring Rockaway Shuttle train length extensions (summer))
# https://www.etany.org/statements/impeding-progress-costing-riders-opto
# manually entering in their data and adding a late night and weekend column
train_area_df['time_based_change'] = False 
train_area_df['time'] = None 
# changing it for 5 and M (A won't change ridership values)
m_index = train_area_df.loc[train_area_df['route_id']=='M'].index.values[0]
train_area_df.loc[m_index, 'time_based_change'] = True
five_index = train_area_df.loc[train_area_df['route_id']=='5'].index.values[0]
train_area_df.loc[five_index, 'time_based_change'] = True

# add time frame column 

# new data frame with new values 
time_adjustments_df = train_area_df[train_area_df['route_id'].isin(['5', 'M'])==True]
time_adjustments_df['time'] = 'Late Night'
def divide_values_by_two(column_list, df):
    for column in column_list: 
        df[column] = df[column] / 2
    return df
time_adjustments_df = divide_values_by_two(['number_of_cars', 'train_length', 'trainset_area', 'capacity_per_car', 'capacity'], time_adjustments_df)
time_adjustments_df = pd.concat([time_adjustments_df, time_adjustments_df[time_adjustments_df['route_id']=='M']])
time_adjustments_df.reset_index(drop=True, inplace=True)
time_adjustments_df.loc[2, 'time'] = 'Weekend'

train_area_df = pd.concat([train_area_df, time_adjustments_df])


# Saving the DataFrame
if not os.path.exists(f'{parent_dir}/saved_data'):
    os.makedirs(f'{parent_dir}/saved_data')
train_area_df.to_csv(f"{parent_dir}/saved_data/length_of_each_train.csv")