import config
import calendar
from datetime import datetime, timedelta
from breeze_chms_api import breeze
import os
import time
import tempfile
from pathlib import Path
import pandas as pd

# Initialize Breeze API
breeze_api = breeze.breeze_api(breeze_url=config.church_domain_url, api_key=config.breeze_api_key)

donatedFoodPounds  = 150244    # From https://docs.google.com/spreadsheets/d/1lMoOrWVFC-Z0FnySEQQiuVBi2IzmAyDnhZhCCsuiYnU/edit?usp=sharing
donatedFoodValue = 1.93 * donatedFoodPounds


def get_pantry_date():
    current_run = datetime.now()
    return current_run + timedelta(days=3 - current_run.weekday())

def convert_to_datetime(date):
    if isinstance(date, str):
        return datetime.strptime(date, '%m/%d/%Y')
    return date

def get_pantry_dates(start_date, end_date):
    start_date = convert_to_datetime(start_date)
    end_date = convert_to_datetime(end_date)
    
    thursdays = []
    current_date = start_date
    while current_date.weekday() != 3:  # 3 corresponds to Thursday
        current_date += timedelta(days=1)
        
    while current_date <= end_date:
        thursdays.append(current_date)
        current_date += timedelta(days=7)
        
    return thursdays

def get_pantry_dates_this_month(onedate):
    last_day_of_month = calendar.monthrange(onedate.year, onedate.month)[1]
    return get_pantry_dates(onedate.replace(day=1), onedate.replace(day=last_day_of_month))

def fetch_event_attendance(pantry_datetime):
    pantry_date = pantry_datetime.strftime('%m/%d/%Y')
    events = breeze_api.list_events(start=pantry_date, end=pantry_date, category_id=55532, details=0)
    if not events:
        raise ValueError(f"No events found on {pantry_date}")
    return breeze_api.list_attendance(instance_id=events[0]['id'])

def clean(word):
    if word == 0:
        return 'Unknown'
    return word.strip().title()

people_info = {
    'Family Size' : {'count': 0, 'key': '1515006285'},
    'Children' :    {'count': 0, 'key': '1515006286'},
    'Adults' :      {'count': 0, 'key': '1515006287'},
    'Seniors' :     {'count': 0, 'key': '1515006288'}, 
}

def get_city_and_families(attendance):
    result = {}

    for person, data in attendance.items():
        time.sleep(3.5)  # Recommended delay by Breeze API- See https://support.breezechms.com/hc/en-us/articles/360001324153-API-Advanced-Custom-Development
        profile = breeze_api.get_person_details(person_id=person)
        data['City'] = clean(profile['details']['589696826'][0]['city'])

        for key, info in people_info.items(): 
            try:
                data[key] = int(profile['details'].get(info['key'], 0)) 
                info['count'] += data['visits'] * data[key]
            except:
                print(f"Missing Food Pantry Shopper Details, {key} for {profile['id']}: {profile['first_name']} {profile['last_name']}")
                data[key] = int(0);
        
        if data['Family Size'] == 0:
            print(f"Missing 'Total in House' for {person}.")
        if data['Family Size'] != data['Children'] + data['Adults'] + data['Seniors']:
            print(f"Age breakdowns do not add up to total for {person}.")
        
        result[person] = data
        
    return pd.DataFrame.from_dict(result, orient='index')

def summarize(report, weeks_reported):
    MealsPerWeek = 15
    numberOfSeniors = 25
    num_weeks = len(weeks_reported)
    
    SeniorCenter = {
        'Households': numberOfSeniors,
        'Individuals': numberOfSeniors * num_weeks,
        'Meals': MealsPerWeek * numberOfSeniors * num_weeks,
        'Over 60': numberOfSeniors * num_weeks
    }

    def calculate_row(filtered_data, town=None):
        row = {
            'Town': town or 'TOTAL',
            'Households': len(filtered_data),
            'Individuals': (filtered_data['Family Size'] * filtered_data['visits']).sum(),
            'Meals': MealsPerWeek * (filtered_data['Family Size'] * filtered_data['visits']).sum(),
            'Over 60': (filtered_data['Seniors'] * filtered_data['visits']).sum(),
            'Children': (filtered_data['Children'] * filtered_data['visits']).sum()
        }
        if town == 'Newmarket' or town is None:
            for key, value in SeniorCenter.items():
                row[key] += value
        return row

    summary = []

    # Calculate rows for each town.
    for town in report['City'].unique():
        filtered = report.loc[report['City'] == town]
        summary.append(calculate_row(filtered, town))

    # Calculate totals
    summary.append(calculate_row(report))

    return summary


def get_trend(attendance_by_date, people_data, report_dates):
    base_senior_count = 25
    people_fed = []
    families_fed = []
    children_fed = []
    seniors_fed = []
    
    for pantry_day, shoppers in attendance_by_date.items():
        individuals = base_senior_count
        children = 0
        seniors = base_senior_count
        for person in shoppers:
            individuals += people_data.at[person['person_id'], 'Family Size']
            children += people_data.at[person['person_id'], 'Children']
            seniors += people_data.at[person['person_id'], 'Seniors']
        
        people_fed.append(individuals)
        families_fed.append(len(shoppers))
        children_fed.append(children)
        seniors_fed.append(seniors)

    return pd.DataFrame({
        'Date': report_dates,
        'People Fed': people_fed,
        'Families Fed': families_fed,
        'Children Fed': children_fed,
        'Seniors Fed': seniors_fed,
        'Value': [round(p * donatedFoodValue / sum(people_fed), 2) for p in people_fed] 
    })


def main():
    local_path = os.path.normpath(os.path.expanduser('~/Desktop'))
    if not os.path.exists(local_path):
        local_path = tempfile.gettempdir()

    pantry_date = get_pantry_date()
    attendance = {}
    attendance_by_date = {}

    # report_dates = get_pantry_dates_this_month(pantry_date)
    report_dates = get_pantry_dates('12/1/2024', '12/31/2024')
    for pantry_date in report_dates:
        clients = fetch_event_attendance(pantry_date)
        attendance_by_date[pantry_date] = clients
        for rec in clients:
            if rec['person_id'] in attendance:
                attendance[rec['person_id']]['visits'] += 1
            else:
                attendance[rec['person_id']] = {'visits': 1}
    
    people_data = get_city_and_families(attendance)
      
    trend = get_trend(attendance_by_date, people_data, report_dates)
      
    people_fed_file = os.path.join(local_path, 'trend.csv')
    trend.to_csv(people_fed_file, index=False)
    print(f'Wrote {people_fed_file}')

    summary = summarize(people_data, report_dates)
    
    summary_file = os.path.join(local_path, 'summary.csv')
    
    pd.DataFrame(summary).to_csv(summary_file, index=False)
    print(f'Wrote {summary_file}')

    # USDA has requested that we report only counts for Newmarket and Newfields. 
    # The Pantry has decided that any people not from Newfields will be reported as from Newmarket. 
    people_data.loc[people_data['City'] != 'Newfields', 'City'] = 'Newmarket'
    summary = summarize(people_data, report_dates)
    usda_file = os.path.join(local_path, 'USDA_summary.csv')
    pd.DataFrame(summary).to_csv(usda_file, index=False)
    print(f'Wrote {usda_file}')
    print(pd.DataFrame(summary))

if __name__ == "__main__":
    main()
