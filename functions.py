import pandas as pd
pd.options.display.float_format = '{:,.0f}'.format
import datetime
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
    mapping = {
        'Weekday': ['Weekday', 'L0S1', 'L0S4', 'L0S7'],
        'Saturday': ['Saturday', 'L0S2', 'L0S5', 'L0S8'],
        'Sunday': ['Sunday', 'L0S3', 'L0S6', 'L0S9']
        }
    for trip_id in dataframe[column_name]:
        for day, mapped_value_list in mapping.items():
            for value in mapped_value_list:
                if value in trip_id:
                    day_of_week_list.append(day)
                    break
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
        dataframe = pd.concat([dataframe, new_days_rows], ignore_index=True)
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

def choose_streamlit_time_freq_data(time_freq:str):
    if time_freq == 'Hourly':
        returned_df = load_original_data('hourly_route_trip_freq')
    elif time_freq == "Daily":
        returned_df = load_original_data('daily_route_trip_freq')
    elif time_freq == "Train Time Interval":
        returned_df = load_original_data('trip_interval_route_freq')
    elif time_freq == "Overall":
        daily_df = load_original_data('daily_route_trip_freq')
        daily_df.reset_index(inplace=True)
        upsampled_daily_df = upsample_weekday_values(daily_df, day_of_week_column='Day of Week')
        returned_df = upsampled_daily_df.groupby('Service').mean()
        returned_df = returned_df.drop(columns=['Day of Week'])
        returned_df = returned_df.round()
        returned_df = returned_df.astype({"TPH": 'int'
                                        , "Wait Time (Min.)": 'int'})
    return returned_df

def filter_streamit_data(dataframe:pd.DataFrame
                         , service_filter=None
                         , time_freq_filter=None
                         , day_filter=None
                         , hour_filter=None):
    if service_filter:
        dataframe = dataframe[dataframe.index.isin(service_filter)]
    if time_freq_filter:
        dataframe = dataframe[dataframe['Time Interval'].isin(time_freq_filter)]
    if day_filter:
        dataframe = dataframe[dataframe['Day of Week'].isin(day_filter)]
    if hour_filter:
        dataframe = dataframe[dataframe['Hour'].isin(hour_filter)]
    return dataframe

def find_difference_in_service_levels(filtered_df_1:pd.DataFrame, filtered_df_2:pd.DataFrame):
    service_1_tph = filtered_df_1['TPH'].mean()
    service_2_tph = filtered_df_2['TPH'].mean()
    service_difference = round(100 * (1 - (service_2_tph / service_1_tph)))
    return service_1_tph, service_2_tph, service_difference

def print_difference_in_service_levels(service_difference:float):
    if service_difference > 0:
        final_str = f"{service_difference}% more frequent"
    elif service_difference < 0:
        final_str = f"{abs(service_difference)}% less frequent"
    elif service_difference == 0:
        final_str = "is equally as frequent"
    return final_str

def streamlit_specific_adjustments(dataframe: pd.DataFrame):
    # renaming some services
    service_replacements_dict = {"H": "Rock. Shuttle"
                                 , "FS": "Fulton Shuttle"
                                 , "GS": "42nd St. Shuttle"}
    dataframe['Service'] = dataframe['Service'].replace(service_replacements_dict)
    # removing marginal services in time intervals 
    # # (e.g.: B will count as late night when starting at 5:55 am)
    dataframe = dataframe[dataframe['Avg. Wait Time (Min.)']<31]
    return dataframe