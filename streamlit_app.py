# Creating Streamlit app
## Imports
import pandas as pd 
import numpy as np
import streamlit as st
st.write(st.__version__)
# from streamlit_dynamic_filters import DynamicFilters
from functions import *


# title 
st.title('NYC Subway Frequencies')
## st.subheader('All Scheduled Subways Services and Stations All of the Time')
st.subheader('Frequencies for all Subway Services and Stations for all Possible Hours')

# data 
### hourly
hourly_route_trip_freq = pd.read_csv("data/hourly_route_trip_freq.csv", index_col=0)
### daily
daily_route_trip_freq = pd.read_csv("data/daily_route_trip_freq.csv", index_col=0)
### time interval
trip_interval_route_freq = pd.read_csv("data/trip_interval_route_freq.csv", index_col=0)


# tab selection 
tab_selector = st.sidebar.radio("How would you like to view the data?",
            ("About", "Table and Charts", "Map", "Fun Facts About the System"))
# st.sidebar.write(f"You selected *{tab_selector}*")
if tab_selector == 'Fun Facts About the System':
    st.caption("""Use this app to find the frequency for any subway service or station
            in the system. Without looking at any schedules, you will
            be able to have an idea of how long a train will take to arrive
            at your station or for the service as a whole
            **To start, please select how you would like to view the data in the sidebar**""")

# if tab_selector == "Table and Charts" or tab_selector == "Map": 

# MAIN SECTION
# user picks the time and level of detail 
left_column, right_column,  = st.columns(2)
with left_column:
    time_freq = st.selectbox(
        "Time Frequency",
        ("Daily", "Train Time Interval", "Hourly"))
    # the user selected filters and the data selection will probably have to be separate
    filtered_df = filter_streamlit_time_freq_data(time_freq)

with right_column:
    level_of_detail = st.selectbox(
        "Service Type",
        ("Service", "Line", "Complex", "Station"))
    level_of_detail_filter_options = filtered_df.index.drop_duplicates()
    level_of_detail_filter = st.multiselect('Select your service(s) to view:'
                                                , level_of_detail_filter_options)
    # this tries to run even if we select "Line", "Complex", "Station"
    filtered_df = filter_streamlit_level_of_detail_data(level_of_detail_filter, filtered_df)

# time_freq control flow 
if time_freq in ['Daily', 'Hourly']:
    # daily_route_trip_freq
    filtered_df
    st.sidebar.write(f"""The *{time_freq}* schedule has 3 categeories:
                     Weekday, Saturdays, and Sundays.""")
elif time_freq == 'Train Time Interval':
    filtered_df
    st.sidebar.markdown(f"""The *{time_freq}* schedule has 6 categories:""")
    st.sidebar.markdown("""
                - *Late Night*: Midnight to 6 am, all days
                - *Weekend*: All weekends outside of late nights
                - *Rush Hour AM*: Weekdays from 6:30 am to 9:30 am
                - *Midday*: Weekdays from 9:30 am to 3:30 pm
                - *Rush Hour PM*: Weekdays from 3:30 pm to 8 pm
                - *Evenings*: Weekdays from 8 pm to midnight""")

## notes added depending on time_freq
