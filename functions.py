import pandas as pd
import datetime
import time
import calendar 
from io import StringIO
import streamlit as st
import requests


def determine_train_time_intervals(arrival_time, day_of_week: str):
    arrival_time = arrival_time.time()
    train_time_interval = None
    if datetime.time(0, 0) <= arrival_time < datetime.time(6, 30):
        train_time_interval = 'Late Night'
    elif day_of_week in ['Saturday', 'Sunday']:
        train_time_interval = 'Weekend'
    elif datetime.time(6, 30) <= arrival_time < datetime.time(9, 30):
        train_time_interval = 'Rush Hour AM'
    elif datetime.time(9, 30) <= arrival_time < datetime.time(15, 30):
        train_time_interval = 'Midday'
    elif datetime.time(15, 30) <= arrival_time < datetime.time(20, 0):
        train_time_interval = 'Rush Hour PM'
    elif datetime.time(20, 0) <= arrival_time <= datetime.time(23, 59):
        train_time_interval = 'Evening'
    return train_time_interval

def scale_time_intervals_to_hour(df_grouped_at_interval_level: pd.DataFrame):
    for idx, row in df_grouped_at_interval_level.iterrows():
        if row['train_time_interval'] == 'Late Night':
            new_tph = (row['trains_per_hour'] / 3) / 6.5 # multiply by days ratio and hours ratio 
            df_grouped_at_interval_level.at[idx, 'trains_per_hour'] = new_tph
        elif row['train_time_interval'] == 'Weekend':
            new_tph = (row['trains_per_hour'] / 2) / 17.5 # multiply by days ratio and hours ratio 
            df_grouped_at_interval_level.at[idx, 'trains_per_hour'] = new_tph
        elif row['train_time_interval'] == 'Rush Hour AM':
            new_tph = row['trains_per_hour'] / 3 # multiply by days ratio and hours ratio 
            df_grouped_at_interval_level.at[idx, 'trains_per_hour'] = new_tph
        elif row['train_time_interval'] == 'Midday':
            new_tph = row['trains_per_hour'] / 6 # multiply by days ratio and hours ratio 
            df_grouped_at_interval_level.at[idx, 'trains_per_hour'] = new_tph
        elif row['train_time_interval'] == 'Rush Hour PM':
            new_tph = row['trains_per_hour'] / 4.5 # multiply by days ratio and hours ratio 
            df_grouped_at_interval_level.at[idx, 'trains_per_hour'] = new_tph
        elif row['train_time_interval'] == 'Evening':
            new_tph = row['trains_per_hour'] / 4 # multiply by days ratio and hours ratio 
            df_grouped_at_interval_level.at[idx, 'trains_per_hour'] = new_tph
    return df_grouped_at_interval_level

def group_into_day_type(dataframe: pd.DataFrame, column_name:str):    
    day_of_week_list = []
    for x in dataframe[column_name]:
        if 'Weekday' in x or 'L0S1' in x:
            day_of_week_list.append('Weekday')
        elif 'Saturday' in x or 'L0S2' in x:
            day_of_week_list.append('Saturday')
        elif 'Sunday' in x or 'L0S3' in x:
            day_of_week_list.append('Sunday')
    dataframe['day_of_week'] = day_of_week_list
    return dataframe

def upsample_weekday_values(dataframe: pd.DataFrame, day_of_week_column: str):
    # returns the values as days as numbers
    day_number_mapping = list(calendar.day_name)
    new_rows = dataframe[dataframe[day_of_week_column]=='Weekday'].copy()
    dataframe[day_of_week_column] = dataframe[day_of_week_column].replace(
                                                    {'Weekday': 0, 'Saturday': 5,'Sunday': 6})
    for idx, day_name in enumerate(day_number_mapping[1:5]):
        new_days_rows = new_rows.copy()
        new_days_rows[day_of_week_column] = new_rows[day_of_week_column].replace({'Weekday': idx+1})
        dataframe = dataframe.append([new_days_rows], ignore_index=True)
    return dataframe

def x_minute_subway(station_df:pd.DataFrame, minutes:int):
    max_distance_meters = 80 * minutes
    meters_to_station_in_x_minutes = []
    for item in station_df['tph']:
        result = max_distance_meters - ((60 / item) * 80)
        if result < 0:
            result = 0
        meters_to_station_in_x_minutes.append(result)
    return meters_to_station_in_x_minutes

def load_original_data(file_name:str):
    url = f'https://raw.githubusercontent.com/gregfeliu/NYC-Subway-Frequencies/main/data/{file_name}.csv'
    response = requests.get(url)
    if response.status_code == 200:
        return pd.read_csv(StringIO(response.text), index_col=0)
    else:
        st.error("Failed to load data from GitHub.")
        return None

def filter_streamlit_time_freq_data(time_freq:str):
    if time_freq == 'Hourly':
        returned_df = load_original_data('hourly_route_trip_freq')
    elif time_freq == "Daily":
        returned_df = load_original_data('daily_route_trip_freq')
    elif time_freq == "Train Time Interval":
        returned_df = load_original_data('trip_interval_route_freq')
    return returned_df


