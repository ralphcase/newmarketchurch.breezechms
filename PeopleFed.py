import config
import calendar
import logging
import argparse
from datetime import datetime, timedelta
from breeze_chms_api import breeze
import os
import time
import tempfile
from pathlib import Path
import pandas as pd

# Initialize logging 
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Breeze API
breeze_api = breeze.breeze_api(breeze_url=config.church_domain_url, api_key=config.breeze_api_key)

# Configuration 
donated_food_pounds = 0 # From https://docs.google.com/spreadsheets/d/1lMoOrWVFC-Z0FnySEQQiuVBi2IzmAyDnhZhCCsuiYnU/edit?usp=sharing 
donated_food_value_per_pound = 1.93 # From the NH Food Bank
category_id = 55532 
sunrise_center_count = 25
meals_per_week = 15 

people_info = {
    # The keys are the Breeze keys for the profile fields.
    'Family Size' : {'count': 0, 'key': '1515006285'},
    'Children' :    {'count': 0, 'key': '1515006286'},
    'Adults' :      {'count': 0, 'key': '1515006287'},
    'Seniors' :     {'count': 0, 'key': '1515006288'}, 
}


def get_pantry_date(): 
    """Get the pantry date based on the current date.""" 
    current_run = datetime.now().date()
    return current_run + timedelta(days=3 - current_run.weekday())
    

def convert_to_date(date):
    """Convert string date to date object if necessary."""
    if isinstance(date, str):
        return datetime.strptime(date, '%m/%d/%Y')
    return date


def get_pantry_dates(start_date, end_date):
    """Get all Thursdays within the given date range."""
    start_date = convert_to_date(start_date)
    end_date = convert_to_date(end_date)
    
    thursdays = []
    current_date = start_date
    while current_date.weekday() != 3:  # 3 corresponds to Thursday
        current_date += timedelta(days=1)
        
    while current_date <= end_date:
        thursdays.append(current_date)
        current_date += timedelta(days=7)
        
    return thursdays


def get_pantry_dates_this_month(onedate):
    """Get all pantry dates for the current month."""
    onedate = convert_to_date(onedate)
    last_day_of_month = calendar.monthrange(onedate.year, onedate.month)[1]
    return get_pantry_dates(onedate.replace(day=1), onedate.replace(day=last_day_of_month))


def fetch_event_attendance(pantry_datetime):
    """Fetch event attendance for a given pantry date."""
    pantry_date = pantry_datetime.strftime('%m/%d/%Y')
    events = breeze_api.list_events(start=pantry_date, end=pantry_date, category_id=55532, details=0)
    if not events:
        raise ValueError(f"No events found on {pantry_date}")
    return breeze_api.list_attendance(instance_id=events[0]['id'])


def clean(word):
    """Clean and format a word."""
    if word == 0:
        return 'Unknown'
    return word.strip().title()


def get_city_and_families(attendance):
    """Get city and family details from attendance."""
    result = {}

    for person, data in attendance.items():
        time.sleep(3.5)  # Recommended delay by Breeze API - See https://support.breezechms.com/hc/en-us/articles/360001324153-API-Advanced-Custom-Development
        profile = breeze_api.get_person_details(person_id=person)
        data['City'] = clean(profile['details']['589696826'][0]['city'])

        for key, info in people_info.items(): 
            try:
                data[key] = int(profile['details'].get(info['key'], 0)) 
                info['count'] += data['visits'] * data[key]
            except Exception as e:
                logging.warning(f"Missing Food Pantry Shopper Details, {key} for {profile['id']}: {profile['first_name']} {profile['last_name']}")
                data[key] = int(0);
        
        if data['Family Size'] == 0:
            logging.warning(f"Missing 'Total in House' for {person}.")
        if data['Family Size'] != data['Children'] + data['Adults'] + data['Seniors']:
            logging.warning(f"Age breakdowns do not add up to total for {person}.")
        
        result[person] = data
        
    return pd.DataFrame.from_dict(result, orient='index')


def add_seniors(people_data):
    for i in range(sunrise_center_count):
        new_row = {
                'visits': people_data['visits'].max(), 
                'City':'Newmarket', 
                'Family Size':1, 
                'Children':0, 
                'Adults':0, 
                'Seniors':1
        }
        people_data = pd.concat([people_data, pd.DataFrame([new_row])], ignore_index = False)
          
    return people_data

    
def summarize(report, weeks_reported):
    """Summarize data by town."""
    num_weeks = len(weeks_reported)
    
    SeniorCenter = {
        'Households': sunrise_center_count,
        'Individuals': sunrise_center_count * num_weeks,
        'Meals': meals_per_week * sunrise_center_count * num_weeks,
        'Over 60': sunrise_center_count * num_weeks
    }

    def calculate_row(filtered_data, town=None):
        row = {
            'Town': town or 'TOTAL',
            'Households': len(filtered_data),
            'Individuals': (filtered_data['Family Size'] * filtered_data['visits']).sum(),
            'Meals': meals_per_week * (filtered_data['Family Size'] * filtered_data['visits']).sum(),
            'Over 60': (filtered_data['Seniors'] * filtered_data['visits']).sum(),
            'Children': (filtered_data['Children'] * filtered_data['visits']).sum()
        }
        return row

    summary = []

    # Calculate rows for each town.
    for town in report['City'].unique():
        summary.append(calculate_row(report.loc[report['City'] == town], town))

    # Calculate totals
    summary.append(calculate_row(report))

    return summary


def get_trend(attendance_by_date, people_data, report_dates, donated_food_value=0):
    """Get trend data from attendance by date."""
    people_fed = []
    families_fed = []
    children_fed = []
    seniors_fed = []
    
    for pantry_day, shoppers in attendance_by_date.items():
        individuals = 0
        families = 0
        seniors = 0
        children = 0
        if len(shoppers) > 20:
            # If there were only a few shoppers, assume the pantry was closed and there was no distribution at the Sunrise Center.
            individuals += sunrise_center_count
            families += sunrise_center_count
            seniors += sunrise_center_count
        
        for person in shoppers:
            individuals += people_data.at[person['person_id'], 'Family Size']
            families += 1
            children += people_data.at[person['person_id'], 'Children']
            seniors += people_data.at[person['person_id'], 'Seniors']
        
        people_fed.append(individuals)
        families_fed.append(families)
        children_fed.append(children)
        seniors_fed.append(seniors)

    return pd.DataFrame({
        'Date': report_dates,
        'People Fed': people_fed,
        'Families Fed': families_fed,
        'Children Fed': children_fed,
        'Seniors Fed': seniors_fed,
        'Value': [round(p * donated_food_value / sum(people_fed), 2) for p in people_fed] 
    })


def write_file(data, filename):
    """Write a dataframe to a csv file."""
    local_path = os.path.normpath(os.path.expanduser('~/Desktop'))
    if not os.path.exists(local_path):
        local_path = tempfile.gettempdir()

    file = os.path.join(local_path, filename)
    data.to_csv(file, index=False)
    logging.info(f'Wrote {file}')

    return


def main():
    # Create the argument parser 
    parser = argparse.ArgumentParser(description="A simple command line argument parser for the report dates") 
    # Add arguments 
    parser.add_argument('-f', '--from_date', type=str, help='Start date of the report. If omitted, the default is the first day of the month of the to_date.') 
    parser.add_argument('-t', '--to_date', type=str, help='End date of the report. If omitted, the default is the current date.') 
    parser.add_argument('-d', '--donated', type=str, help='Donated food for the report period (in pounds)') 
    # Parse the arguments 
    args = parser.parse_args()
    
    end_date = convert_to_date(args.to_date or get_pantry_date())

    report_dates = get_pantry_dates(args.from_date, end_date) if args.from_date else get_pantry_dates(end_date.replace(day=1), end_date)
    print("Building People Fed reports for:")
    for date in report_dates:
        print(date.strftime("%m/%d/%Y"))

    donated_food = args.donated or donated_food_pounds
    
    attendance = {}
    attendance_by_date = {}

    # Collect the Attendance for each pantry date in the report.
    for pantry_date in report_dates:
        clients = fetch_event_attendance(pantry_date)
        attendance_by_date[pantry_date] = clients
        for rec in clients:
            attendance[rec['person_id']] = {'visits': attendance.get(rec['person_id'], {'visits': 0})['visits'] + 1}

    # Add in the additional data needed for each attendee.
    people_data = get_city_and_families(attendance)

    people_data = add_seniors(people_data)
      
    trend = get_trend(attendance_by_date, people_data, report_dates, donated_food_value_per_pound * donated_food)   
    write_file(trend, 'trend.csv')

    summary = summarize(people_data, report_dates)
    write_file(pd.DataFrame(summary), 'summary.csv')

    # USDA has requested that we report only counts for Newmarket and Newfields. 
    # The Pantry has decided that any people not from Newfields will be reported as from Newmarket. 
    people_data.loc[people_data['City'] != 'Newfields', 'City'] = 'Newmarket'
    summary = summarize(people_data, report_dates)
    write_file(pd.DataFrame(summary), 'USDA_summary.csv')
    print(pd.DataFrame(summary))


if __name__ == "__main__":
    main()
