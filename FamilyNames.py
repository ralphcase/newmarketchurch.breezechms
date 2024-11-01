# For each person in the input People file, use the Breeze API to check for a spouse.
# Add a column with the two names together and remove the duplicate if both spouses are in the input file.

import sys
import os
from collections import OrderedDict
from datetime import datetime, timedelta, date
import time
import urllib.parse
import numpy as np
import pandas as pd

# Set up Breeze API wrapper
from breeze_chms_api import breeze

def help():
    print("""
    This script takes one argument - the name of a giving file.
    
    To create a giving file, select the People you want and 'Download as Excel'. 
    """)
    

# Get the source file for the giving report.
try:
    givingreport = sys.argv[1]
except IndexError:
    help()
    quit()
    
output_file = r"AddressNames.csv"

directory_path = os.path.dirname(os.path.abspath(givingreport))
output_file = os.path.join(directory_path, output_file)

# Read in the downloaded Excel file 
gifts = pd.read_excel(givingreport)
print('{count} people in input.'.format(count = len(gifts.index)))

# Initialize API 
import config
breeze_api = breeze.breeze_api(breeze_url=config.church_domain_url, api_key=config.breeze_api_key)

output = []

# Copy these fields from the input to the output.
output_fields = [
    'first_name',
    'last_name',
    'street_address',
    'city',
    'state',
    'zip',
]

for index, gift in gifts.iterrows():
    if pd.notna(gift['Breeze ID']):
        time.sleep(3.5)       # https://support.breezechms.com/hc/en-us/articles/360001324153-API-Advanced-Custom-Development recommends a 3.5 second delay.
        row = OrderedDict()
        person = breeze_api.get_person_details(person_id = gift['Breeze ID'])
        row['person_id'] = person['id']
        fullname = person['first_name'] + ' ' + person['last_name']
        family = person['family']
        if len(family) > 0:
            for member in family:
                if member['person_id'] == person['id']:
                    if member['role_name'] not in ['Head of Household', 'Spouse']:
                        # The giver is not a spouse or head of household, so don't look for a partner.
                        fullname = person['first_name'] + ' ' + person['last_name']
                        break
                else:
                    if member['role_name'] in ['Head of Household', 'Spouse']:
                        row['spouse_id'] = member['person_id']
                        if person['last_name'] == member['details']['last_name']:
                            # Partners have the same last name, so use it once.
                            fullname = person['first_name'] + ' & ' + member['details']['first_name'] + ' ' + person['last_name']
                        else: 
                            # Partners have different last names; use both.
                            fullname = person['first_name'] + ' ' + person['last_name'] + ' & ' + member['details']['first_name'] + ' ' + member['details']['last_name'] 
        row['name'] = fullname
        for field in output_fields:
            row[field] = person[field]

        # Look for the same spouses already in the output. Include them only if they're not already there.
        found = False
        for already in output:
            if 'spouse_id' in row and already['person_id'] == row['spouse_id'] and already['spouse_id'] == row['person_id']:
                found = True
                break
        
        if not found:
            output.append(row)

pd.DataFrame(output).to_csv(output_file, index=False)
print('Wrote {file}'.format(file = output_file))
