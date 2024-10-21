# Creating Streamlit app
## Imports
import pandas as pd 
import numpy as np
import streamlit as st
from functions import *


# title 
st.title('NYC Subway Frequencies')
# st.subheader('Scheduled Subways Service Frequencies for Any Time, Day or Night')
# st.subheader('Frequencies for all Subway Services and Stations for all Possible Hours')
st.caption("""Use this app to find the frequency for any subway service or station
        in the system. Without looking at any schedules, you will
        be able to estimate how long it will take for your service to arrive.""")
st.caption("""**To start, please select which time frequency and service you would like to view below.**""")

# data 
### hourly
hourly_route_trip_freq = load_original_data('hourly_route_trip_freq')
### daily
daily_route_trip_freq = load_original_data('daily_route_trip_freq')
### time interval
trip_interval_route_freq = load_original_data('trip_interval_route_freq')

# tab selection 
tab_selector = st.sidebar.radio("How would you like to view the data?",
            ("Service Frequencies", "Service Comparisons", "Appendix"))

if tab_selector == "Service Frequencies":
    # MAIN SECTION
    # user picks the time granularity
    left_column, right_column, = st.columns(2)
    with left_column:
        time_freq = st.selectbox(
            "Time Frequency",
            ("Train Time Interval", "Daily", "Hourly"))
        filtered_df = choose_streamlit_time_freq_data(time_freq)
    # user filters the data 
    with right_column:
        level_of_detail_filter_options = filtered_df.index.drop_duplicates()
        level_of_detail_filter = st.multiselect('Select which service(s):'
                                                    , level_of_detail_filter_options)
        if level_of_detail_filter:
            filtered_df = filter_streamit_data(filtered_df, service_filter=level_of_detail_filter)
        if time_freq == 'Train Time Interval':
            time_int_filter_options = filtered_df['Time Interval'].drop_duplicates()
            time_int_filter = st.multiselect('Select which time interval(s):'
                                                , time_int_filter_options)
            filtered_df = filter_streamit_data(filtered_df, time_freq_filter=time_int_filter)
        elif time_freq == 'Daily' or time_freq=='Hourly':
            day_filter_options = filtered_df['Day of Week'].drop_duplicates()
            day_filter = st.multiselect('Select which day(s):'
                                                , day_filter_options)
            filtered_df = filter_streamit_data(filtered_df, day_filter=day_filter)
            if time_freq=='Hourly':
                hour_filter_options = filtered_df['Hour'].drop_duplicates()
                hour_filter = st.multiselect('Select which hour(s):'
                                                , hour_filter_options)
                filtered_df = filter_streamit_data(filtered_df, hour_filter=hour_filter)
    # bottom section
    st.divider()
    filtered_df
    
elif tab_selector=="Service Comparisons":
    # compare two services
    left_column, right_column,  = st.columns(2)
    with left_column:
        # one time freq 
        time_freq = st.selectbox(
            "Time Frequency",
            ("Overall", "Train Time Interval", "Daily", "Hourly"))
        filtered_df = choose_streamlit_time_freq_data(time_freq)
        # filters
        level_of_detail_filter_options = filtered_df.index.drop_duplicates()
        if time_freq == 'Train Time Interval':
            time_int_filter_options = filtered_df['Time Interval'].drop_duplicates()
            # one time intervals 
            time_int_filter = st.selectbox('Select which time interval:'
                                                , time_int_filter_options)
            filtered_df = filter_streamit_data(filtered_df, time_freq_filter=[time_int_filter])
        elif time_freq == 'Daily' or time_freq=='Hourly':
            day_filter_options = filtered_df['Day of Week'].drop_duplicates()
            # one day 
            day_filter = st.selectbox('Select which day:'
                                                , day_filter_options)
            filtered_df = filter_streamit_data(filtered_df, day_filter=[day_filter])
            if time_freq=='Hourly':
                hour_filter_options = filtered_df['Hour'].drop_duplicates()
                # multiple hours 
                hour_filter = st.multiselect('Select which hour(s):'
                                                , hour_filter_options
                                                , default = 8)
                filtered_df = filter_streamit_data(filtered_df, hour_filter=hour_filter)
    with right_column:
        service_1_selection_options = filtered_df.index.drop_duplicates()
        service_1_selection = st.selectbox('Select which service:'
                                                    , service_1_selection_options
                                                    , placeholder="Please select a service to use in the comparison")
        if service_1_selection:
            filtered_df_service_one = filter_streamit_data(filtered_df, service_filter=[service_1_selection])
        
        service_2_selection_options = filtered_df.index.drop_duplicates()
        if service_1_selection:
            service_2_selection_options = service_2_selection_options.drop(service_1_selection)
        service_2_selection = st.selectbox('Select which service:'
                                                    , service_2_selection_options
                                                    , placeholder="Please select a service to use in the comparison")
        if service_2_selection:
            filtered_df_service_two = filter_streamit_data(filtered_df, service_filter=[service_2_selection])

    # compare service A to service B and show how they perform compared to the rest of the system
        # allow user to pick 2 services (left side, the rest are on the right)
    # determine the difference in frequency
    service_level_1, service_level_2, service_difference = find_difference_in_service_levels(filtered_df_service_one, filtered_df_service_two)
    service_difference_str = print_difference_in_service_levels(service_difference)
    st.divider()
    st.markdown(f"""The **{service_1_selection}** is {service_difference_str} than the **{service_2_selection}** for the time period your selected""")
    st.text(" \n") ## adds a new line
        
    # displaying the differences
    service_1_2_df = pd.concat([filtered_df_service_one, filtered_df_service_two]).reset_index()
    st.bar_chart(data=service_1_2_df
                , x='Service'
                , y="TPH"
                , width=500
                , use_container_width=False
                , color=['#EE352E']
                )

# elif tab_selector == 'Fun Facts About the System':
#     st.caption("""Use this app to find the frequency for any subway service or station
#             in the system. Without looking at any schedules, you will
#             be able to estimate how long a train will take to arrive for a service as a whole.
#             **To start, please select how you would like to view the data in the sidebar**""")

    # Helpful information about the data in the sidebar and displaying the data
elif tab_selector == 'Appendix':
    time_freq = None
    
    st.caption("""Use this app to find the frequency for any subway service or station
            in the system. Without looking at any transit service app, you will
            be able to estimate how long a train will take to arrive
            at your station or for the service as a whole. It also allows you to 
            compare and evaluate different services for future trips.""")
    st.divider()
    st.markdown("""This app uses the [static MTA GTFS Schedule from August 12, 2024 to December 12, 2024](http://web.mta.info/developers/data/nyct/subway/google_transit.zip). 
            The schedule is valid for all planned trips taking into account long term service outages/reroutes. """)
    st.caption("To learn more about the conclusions of this project, go to the project's [GitHub page](https://github.com/gregfeliu/NYC-Subway-Frequencies/tree/main?tab=readme-ov-file)")

if time_freq in ['Daily', 'Hourly']:
    st.sidebar.write(f"""The *{time_freq}* schedule has 3 categeories:
                    Weekday, Saturdays, and Sundays.""")
    if tab_selector=="Service Comparisons":
        st.sidebar.write(f"""Note: the **B** service does not appear because it does not run on all days.""")
elif time_freq == 'Train Time Interval':
    st.sidebar.markdown(f"""The *{time_freq}* schedule has 6 categories:""")
    st.sidebar.markdown("""
                - *Late Night*: Midnight to 6 am, all days
                - *Weekend*: All weekends outside of late nights
                - *Rush Hour AM*: Weekdays from 6:00 am to 9:00 am
                - *Midday*: Weekdays from 9:00 am to 4:00 pm
                - *Rush Hour PM*: Weekdays from 4:00 pm to 7 pm
                - *Evenings*: Weekdays from 7 pm to midnight""")
elif time_freq == 'Overall': 
    st.sidebar.markdown(f"""The *{time_freq}* data is for **all** hours, including late night""")

