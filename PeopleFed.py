import config
from datetime import datetime, timedelta
from breeze_chms_api import breeze

# Initialize Breeze API
breeze_api = breeze.breeze_api(breeze_url=config.church_domain_url, api_key=config.breeze_api_key)

def get_pantry_date():
    current_run = datetime.now()
    thursday = current_run + timedelta(days=-4 - current_run.weekday())
    return thursday.strftime('%m/%d/%Y')

def fetch_event_attendance(pantry_date):
    events = breeze_api.list_events(start=pantry_date, end=pantry_date, category_id=55532, details=0)
    if not events:
        raise ValueError(f"No events found on {pantry_date}")
    return breeze_api.list_attendance(instance_id=events[0]['id'])

def get_total_people_and_families(attendance, base_count):
    total_people = base_count
    total_families = len(attendance)
    
    for person in attendance:
        profile = breeze_api.get_person_details(person_id=person['person_id'])
        family_size_key = '1515006285'
        
        if family_size_key in profile['details']:
            total_people += int(profile['details'][family_size_key])
        else:
            print(f"Missing family information for {profile['id']}: {profile['first_name']} {profile['last_name']}")
    
    return total_people, total_families

def main():
    pantry_date = get_pantry_date()
    attendance = fetch_event_attendance(pantry_date)
    
    base_senior_count = 25
    total_people, total_families = get_total_people_and_families(attendance, base_senior_count)
    
    print(f'On {pantry_date}, we fed {total_people} people and {total_families} families.')

if __name__ == "__main__":
    main()
