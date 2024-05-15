# Remove old Communication Management forms

from datetime import datetime

# Breeze forms used
ncc_url = 'https://newmarketchurch.breezechms.com'
breeze_forms = ncc_url + '/forms/entries/'
subscribe_form_id = '460630'

# Set up Breeze API wrapper
from breeze_chms_api import breeze

# Initialize API 
import config
breeze_api = breeze.breeze_api(breeze_url=ncc_url, api_key=config.api_key)

entries = breeze_api.list_form_entries(form_id = subscribe_form_id, details=True)

most_recent_entry = {}
for e in entries:
    recent = datetime.strptime(e['created_on'], '%Y-%m-%d %H:%M:%S')
    if e['person_id'] in most_recent_entry:
        if recent > most_recent_entry[e['person_id']]['time']:
            # Delete preious recent and save new recent
            print('removing form entry ' + most_recent_entry[e['person_id']])
            breeze_api.remove_form_entry(entry_id = most_recent_entry[e['person_id']]['id'])
            most_recent_entry[e['person_id']] = {'time': recent, 'id': e['id']}
        else:
            # Delete entry e
            print('removing form entry ' + e['id'])
            breeze_api.remove_form_entry(entry_id = e['id'])
    else:
        most_recent_entry[e['person_id']] = {'time': recent, 'id': e['id']}