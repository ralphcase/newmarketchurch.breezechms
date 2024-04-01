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
    
    To create a giving file, select the criteria you want from https://newmarketchurch.breezechms.com/payments/reports/ and 'Download as Excel'. 
    """)
    

# Get the source file for the giving report.
try:
    givingreport = sys.argv[1]
except IndexError:
    help()
    quit()
    
output_file = r"givers.csv"

directory_path = os.path.dirname(os.path.abspath(givingreport))
output_file = os.path.join(directory_path, output_file)

ncc_url = r"https://newmarketchurch.breezechms.com"

# Read in the downloaded Excel file 
gifts = pd.read_excel(givingreport)
print('{count} people in input.'.format(count = len(gifts.index)))

# Initialize API 
import config
breeze_api = breeze.breeze_api(breeze_url=ncc_url,
                               api_key=config.api_key)

output = []

fields = [
    'first_name',
    'last_name',
    'street_address',
    'city',
    'state',
    'zip',
]

for index, gift in gifts.iterrows():
    if pd.notna(gift['Person ID']) and gift['Fund(s)'] != 'help offset the processing fee':
        time.sleep(3.5)       # https://support.breezechms.com/hc/en-us/articles/360001324153-API-Advanced-Custom-Development recommends a 3.5 second delay.
        row = OrderedDict()
        person = breeze_api.get_person_details(person_id = gift['Person ID'])
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
                        if person['last_name'] == member['details']['last_name']:
                            # Partners have the same last name, so use it once.
                            fullname = person['first_name'] + ' & ' + member['details']['first_name'] + ' ' + person['last_name']
                        else: 
                            # Partners have different last names; use both.
                            fullname = person['first_name'] + ' ' + person['last_name'] + ' & ' + member['details']['first_name'] + ' ' + member['details']['last_name'] 
        row['name'] = fullname
        for field in fields:
            row[field] = person[field]
        row['Fund(s)'] = gift['Fund(s)']
        
        output.append(row)

pd.DataFrame(output).to_csv(output_file, index=False)
print('Wrote {file}'.format(file = output_file))
