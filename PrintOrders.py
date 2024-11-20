#!/usr/bin/env python
# coding: utf-8

# In[1]:


# This notebook does several things for the weekly online shopping orders:
#
# - Create a print file for the orders.
# - Create a print file for labels to attach to the orders when they are filled.
# - Print out "1-page" summaries with just the refrigerated items. (These are packed seperately.)
# - Check-In shoppers to this week's shopping event for all the orders.
# - Delete old order entries to clean up the Breeze page.

import config

# Breeze forms used
breeze_forms = config.church_domain_url + '/forms/entries/'
order_form_id = '557986'
shopper_form_id = '791210'

# Set up Breeze API wrapper
from breeze_chms_api import breeze

# Initialize API 
breeze_api = breeze.breeze_api(breeze_url=config.church_domain_url, api_key=config.breeze_api_key)


# In[2]:


# Show links to the needed form entries. 
# Shoppers don't actually need to be connected to print orders, but they do need 
# to be connected to be checked in and to run reports.
print("Make sure new shoppers are connected - " + breeze_forms + shopper_form_id)
print("Connect orders to people - " + breeze_forms + order_form_id)


# In[3]:


from datetime import datetime, timedelta

# title_date is the Thursday of this week.
current_run = datetime.now()
thursday = current_run + timedelta(days = 3 - current_run.weekday())
title_date = thursday.strftime('%m/%d/%Y')

# Set this to override the date to a specific data rather than just this week.
# title_date = '1/28/2024'

runmode = 'weekly'
# runmode = 'update'
# last_run is only used if runmode is 'update'.
last_run = '12/06/2023 12:00'

# The number of labels to print for each shopper
number_of_labels = 6


# In[4]:


# Get the exported filename for use in the report.
import os
import tempfile
from pathlib import Path

# local_path = Path(os.environ['TEMP'])
local_path = os.path.normpath(os.path.expanduser('~/Desktop'))
if not os.path.exists(local_path):
    local_path = tempfile.gettempdir()

filename = 'NCC Food Pantry Orders' 
title = filename + ' ' + title_date

# These files are created by this script.
order_pdf_file = os.path.join(local_path, filename +'.pdf')
label_pdf_file = os.path.join(local_path, filename +' labels.pdf')


# In[5]:


# Choose the time period for the orders based on the runmode and current time.

modes = {
    'weekly': 'All orders received this week',
    'update': 'All orders received since {date}'.format(date = last_run),
    'special': 'Special criteria were used.'
    }

# Only process recent orders.
if runmode == 'weekly':
    starttime = datetime.strptime(title_date, '%m/%d/%Y') - timedelta(days=5)
elif runmode == 'update':
    starttime = datetime.strptime(last_run, '%m/%d/%Y %H:%M')
else:
    starttime = datetime.today() - timedelta(days=7)


# In[6]:


# We may want to do something to detect when the form changes in ways that will be a problem.
# form_fields

pickupchoice = 'Select pickup time'


# In[7]:


messages = []

def message(m):
    print(m)
    messages.append(m)


# In[8]:


from collections import OrderedDict
import sys
import numpy as np
import pandas as pd

# Build a DataFrame for all the orders. 
# This code builds the data to look like what's downloaded in an excel file from https://newmarketchurch.breezechms.com/forms/entries/557986.

# Get the order form entries.
online_orders = breeze_api.list_form_entries(form_id = order_form_id, details=True)
# The entry response array has key values that correspond to the form fields.
if online_orders is None:
    print('No orders were found in Breeze.')
    sys.exit()
else:
    ordercount = len(online_orders)
    print('{count} orders in input.'.format(count = ordercount))

# Get the form fields needed to make sense of the entries.
form_fields = breeze_api.list_form_fields(form_id = order_form_id)

for profile_field in breeze_api.get_profile_fields():
    if profile_field['name'] == 'Food Pantry Shopper Details':
        # print(profile_field)
        delivery_field = [field for field in profile_field['fields'] if field['name'] == 'Approved for Delivery'][0]['field_id']

# print(online_orders[0])
# print(form_fields)

# "Join" the order entries with the form fields.

shopper_ids = []
all_api_orders = []

for order in online_orders:
    row = OrderedDict()
    for field, value in order['response'].items():
        existing_field = [f for f in form_fields if f['field_id'] == field]
        if len(existing_field) > 0:
            # If no existing form field, this field has been deleted from the form - skip it.
            field = existing_field[0]
            # 'Name' and 'Address' values are dicts specific to those data types.
            if field['field_type'] == 'name':
                row['Date'] = value['created_on']
                row['Name'] = value['first_name'].strip() + ' ' + value['last_name'].strip()
            elif field['field_type'] == 'address':
                value = [v for v in value if v['is_primary'] == '1'][0]
                # This is a hack. We use '<br />' to delimit separate items in the same field. 
                # We use '<br/>' here only for the line break and not to delimit items.
                row['Address'] = value['street_address'].strip() + '<br/>' + value['city'].strip() + ' ' + value['state'].strip() + ' ' + value['zip'].strip()
            else:
                # If the value is a dict, look it up in the form fields.
                # If it is a list of dicts, look up each and concatenate them with '<br >'.
                if isinstance(value, dict):
                    try:
                        value = [op for op in field['options'] if op['option_id'] == value['value']][0]['name']
                    except IndexError:
                        print(f"Form entry error. No option selected for required field: {field}, and value: {value}.")
                        print(value, order)
                if isinstance(value, list):
                    selections = []
                    for onevalue in value:
                        lookup = [op for op in field['options'] if op['option_id'] == onevalue['value']]
                        if len(lookup) == 0:
                            # The item is not on the form. This is common for older forms as the form usually changes each week.
                            if pd.to_datetime(row['Date']) >= starttime:
                                print("Order from {name} on {date} includes item not on the form.".format(order=order['response'], name = row['Name'], date=row['Date']))
                                print("form field: ", field['name'])
                                print("value:", onevalue)
                        else: 
                            selections.append(lookup[0]['name'].strip())
                    value = '<br />'.join(selections)
            
                row[field['name']] = value

    # Check if delivery is approved.
    if 'delivery' in row[pickupchoice].lower():
        if order['person_id'] is None:
            message('Delivery ordered, but approval could not be checked since the order was not connected to a person.')
        else:
            profile = breeze_api.get_person_details(person_id=order['person_id'])
            if not delivery_field in profile['details'] or not any(d.get('name') == 'Yes' for d in profile['details'][delivery_field]):
                message(f"{profile['first_name']} {profile['last_name']} submitted an order for delivery, but was not approved for delivery.")
                
    # Include only those that match the time period for this run.
    if pd.to_datetime(row['Date']) >= starttime:
        shopper_ids.append(order['person_id'])   
        all_api_orders.append(row)

    # Remove old entries from Breeze.
    if pd.to_datetime(row['Date']) < starttime - timedelta(days = 2):
        breeze_api.remove_form_entry(entry_id = order['id'])

if any(id is None for id in shopper_ids):
    message("Unrecognized shopper. Were all form entries connected to people?")

allorders = pd.DataFrame(all_api_orders, columns=[f['name'] for f in form_fields])

printed = len(allorders.index)
print('{count} orders filtered by date and time.'.format(count = printed))


# In[9]:


# "Hard Code" some items that are usually needed but not available from the forms.

# Recurring shoppers. These people may not check in, but should be counted when we report on shoppers served.
recurringshoppers = [
    '30397442',   # Jay Stillman
    '30908360',   # Julie Walker-Bourbon
    '30396500',   # Britt Gleason
    '30396178',   # Ed Comeau
    '30397394',   # Henry Smith
    '30396002',   # Ashley Bowley
]
shopper_ids.extend(recurringshoppers)

# Additional labels that we can't get from the forms.
paper_order_labels = [
    {
        'shoppername': 'Jay Stillman', 
        'pickup': 'Thursday, 12 - 2pm', 
        'address': ' ', 
        'phone': '659-4911'
    }
    ]

# Replace "NaN" values with blanks.
allorders = allorders.replace(np.nan, '')

printed = len(allorders.index)


# In[10]:


# Check in the shoppers from the order forms for the shopping event.
# Note: All orders must be connected to People to allow check-in.

print('{count} shoppers to check in.'.format(count = len(shopper_ids)))

# Find the shopping event by name and date.
# print(breeze_api.list_calendars())
food_pantry_calendar_id = '55532'
events = breeze_api.list_events(start=title_date, end=title_date, category_id=food_pantry_calendar_id)
shoppingevent = [e for e in events if e['name'] == 'Food Pantry'][0]

eligible_ids = [e['id'] for e in breeze_api.list_eligible_people(instance_id=shoppingevent['id'])]
ineligible_shoppers = []

for id in shopper_ids:
    if id in eligible_ids:
        breeze_api.event_check_in(person_id=id, instance_id=shoppingevent['id'])
    else:
        message(f'Shopper {id} is not eligible to check in.')
        if id is not None:
            person = breeze_api.get_person_details(person_id = id)
            ineligible_shoppers.append(f"{person['first_name']} {person['last_name']} ({id})")

attendance = len(breeze_api.list_attendance(instance_id=shoppingevent['id']))
print('{count} shoppers checked in.'.format(count = attendance))


# In[11]:


# Aggregate multiple orders from the same name.

duporderers = set()

def concatenate(ser):
    # Collect all the requests from all the orders and include each one just once.
    br = '<br />'    # Order request seperator
    contents = set()
    if len(ser) > 1:
        # Keep track of the names on multiple orders so they can be included on the cover sheet. 
        duporderers.add(allorders['Name'].loc[ser.index[0]])
    for elem in ser:
        contents = contents.union(set((str(elem).split(br))))
    contents.discard('')   # Don't keep blank requests.

    # TODO: If there are different addresses on multiple orders from the same person, this code keeps all of them.
    # This overflows the limited size of the labels.

    return br.join(list(contents))
        
allorders = allorders.groupby('Name', as_index=False).aggregate(concatenate)

# allorders = allorders.sort_values(by = 'Pickup Time')
allorders = allorders.sort_values(by = pickupchoice)

deduped = len(allorders.index)
print('{count} orders deduped.'.format(count = deduped))
if len(duporderers) > 0:
    print('Duplicate orders received from {people}'.format(people = duporderers))


# In[12]:


# Collect the summary for only refrigerated items. ("page 1")
# Include only the following fields in the Summary.

headerFields = [
    'Name', 
    'Number of people in household', 
    pickupchoice,
    'Address', 
    'Email', 
    'Phone', 
    # 'Anything else we should know? ',
    'PLEASE LIST ANY ALLERGIES/DIETARY RESTRICTIONS - Just type "n/a" if none.',
    'Notes for your order (example: low sodium, low sugar, any items you might enjoy.)'
    # 'Indicate any dietary restrictions (Peanut allergy, low sodium, vegetarian only, etc.)',
]
refrigFields = [
    # 'FROZEN PROTEINS - Please select only items you need; every attempt will be made to fill at least 2-3 items per family', 
    'FROZEN ITEMS',
    'REFRIGERATED ITEMS', 
    # 'Notes for Fresh and Frozen Items Only. Please use Special Notes section at beginning of order for other requests.',
]
summary = allorders[headerFields + refrigFields]
allorders = allorders.drop(columns = refrigFields)


# In[13]:


# Define HTML templates using Jinja2 for printing the data.

from jinja2 import Template

# Template for the whole report, including style.

orders = Template('''
<!DOCTYPE html>
<style>
    h1 { 
            font-family: Arial;
        }
    table tr td { font-family: Arial; font-size: 4mm; }
    table { width: 100%; }
    th { font-family: Arial; font-size: 6mm; }
    td { border-bottom: 1px solid #ddd; }
    td.category { width: 35%; }
</style>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width"/>
<title>{{title}}</title>
</head>
<body>
{{body}}
</body>
</html>
''')

# Template for each shopper
shopperhtml = Template('''
<h1 style="page-break-before:right;" class="shopper-name">PANTRY ORDER FORM ({{date}})</h1>
<table>
<thead><tr><th colspan=2>{{shoppername}}</th></tr></thead>
{{data}}
</table>
''')

coversheet = Template('''
<h2>NCC Pantry Order Print Cover Sheet for {{date}}</h2>
<dl>
<dt>Messages</dt>
<dd>
{% for m in messages %}
    {{m}}</br>
{% endfor %}
</dd>
<dt>Total number of orders in this print file</dt>
<dd><b>{{deduped}}</b></dd>
<dt>Total number people Checked in</dt>
<dd><b>{{checkin}}</b></dd>
<dt>Order forms in input file (before removing old and duplicate orders)</dt>
<dd>{{received}}</dd>
<dt>Orders for Gordon Ave</dt>
<dd>{{gordonave}}</dd>
<dt>Printing orders since</dt>
<dd>{{starttime}} - {{modemsg}}</dd>
<dt>Report run at</dt>
<dd>{{runtime}}</dd>
<dt>Input File</dt>
<dd>{{input_file}}</dd>
<dt>Output File</dt>
<dd>{{output_file}}</dd>
{% if dupers|length > 0 %}
<dt>Multiple Orders received from</dt>
<dd>
{% for duper in dupers %}
    {{duper}}</br>
{% endfor %}
</dd>
{% endif %}
{% if ineligible|length > 0 %}
<dt>Order form from ineligible shopper. Probably need a valid Shopper Information Form.</dt>
<dd>
{% for shopper in ineligible %}
    {{shopper}}</br>
{% endfor %}
</dd>
{% endif %}
</dl>
''')

sectionheader = '''
<h1 style="page-break-before:always;">One Page Summaries for Refrigerated Items</h1>
'''

# Template for each row
rowhtml = Template('<tr><td class="category">{{category}}</td><td>{{items}}</td></tr>')



# In[14]:


# Format the order forms as html.

def formatshoppers(date, data):
    output = ''
    
    for _, row in data.iterrows():
        rowtext = ''
        # Format each field as a row in a table.
        for i in range(len(data.columns)):
            if row.iloc[i] != "":
                rowtext += rowhtml.render({'category' : data.columns[i],
                                           'items' : row.iloc[i]})
        
        # Create a page using the above table.
        output += shopperhtml.render({'date': date, 'data': rowtext, 'shoppername': row['Name']})
    
    return output


# In[15]:


# Templates for the Bulk item picking pages

bulkheader = Template('<h1 style="page-break-before:right;">{{title}}</h1>')

bulkcategory = Template('''
<h2>{{category}}</h2>
<table>
  <thead>
    <tr><th>Item</th><th>Count</th></tr>
  </thead>
  <tbody>
    {% for item, count in items.items() %}
      <tr><td>{{ item }}</td><td>{{ count }}</td></tr>
    {% endfor %}
  </tbody>
</table>
''')


# In[16]:


# Print out totals or order quantities for refrigerated and frozen items.
from collections import Counter

def formatbulkitems(summary):
    output = ''
    for time in set(summary[pickupchoice]):
        output += bulkheader.render({'title': time})

        for rs in refrigFields:
            totalitems = []
            for item in summary.loc[summary[pickupchoice] == time][rs]:
                totalitems += [it for it in item.split('<br />') if it != '']  
            output += bulkcategory.render({'category': rs, 'items': Counter(totalitems)})

    return output


# In[17]:


# Build the report using Jinja2.

# Cover Sheet
output = coversheet.render({'received': ordercount, 
                            'printed': printed, 
                            'deduped': deduped, 
                            'checkin': attendance,
                            'gordonave': len(allorders[allorders['Address'].str.lower().str.contains("gordon")]),
                            'date': title_date,
                            'messages': messages,
                            'input_file': 'from API',
                            'output_file': order_pdf_file, 
                            'dupers': duporderers,
                            'ineligible': ineligible_shoppers,
                            'starttime': starttime,
                            'modemsg': modes[runmode],
                            'runtime': current_run.strftime("%Y-%m-%d %H:%M:%S"),
                           })

# Full Orders
output += formatshoppers(title_date, allorders) 

# Separator
output += sectionheader

# Refrigerated items
output += formatbulkitems(summary)

output += formatshoppers(title_date, summary)

orders_html = orders.render({'body': output})


# In[18]:


# Define HTML templates using Jinja2 for printing labels

from jinja2 import Template

# Template for the address labels, including style.
# Styled to fit Avery 8163 (2" x 4") labels. https://www.avery.com/help/article/avery-labels-2-inch-x-4-inch

labels = Template('''<!DOCTYPE html>
<style>
    @page {
        margin-top: 0.45in;
        margin-bottom: 0.45in;
        margin-left: 0.0in;
        margin-right: 0.00in;    
        }
.label {
  width: 3.40in;
  height: 1.875in;
  padding-top: 0.0in;
  padding-bottom: 0.125in;
  padding-left: 0.25in;
  padding-right: 0.25in;
  border-width: 0.0in;
  margin-left: 0.125in;
  margin-right: 0.125in;
  margin-top: 0.0in;
  margin-bottom: 0.0in;
  float: left;
  font-family: Arial;
  font-size: 0.9em;
  text-align: left;
  overflow: hidden;
  outline: 0px white;
  page-break-inside: avoid;
}
.name {
  margin-top: 0.125in;
  font-size: 1.5em;
}
</style>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width"/>
</head>
<body>{{body}}</body>
</html>''')

# Template for each shopper
shopperlabel = Template('''
<div class="label">
<p class='name'>{{shoppername}}</p>
<p>{{pickup}}</p>
<p>{{address}}</p>
<p>{{phone}}</p>
</div>
''')



# In[19]:


# Create labels to be attached to the bags for the orders.

output = ''
# Manually add people for paper orders.
for po in paper_order_labels:
    output += number_of_labels * shopperlabel.render(po)

for _, row in allorders.iterrows():
    pickupdelivery = row[pickupchoice]
    if pickupdelivery == 'Delivery' and 'Instructions for Delivery Driver' in row and row['Instructions for Delivery Driver'].strip().lower() not in ['', 'none']:
        pickupdelivery += ": " + row['Instructions for Delivery Driver'] 
    output += number_of_labels * shopperlabel.render({
        'shoppername': row['Name'], 
        'pickup': pickupdelivery,
        'address': row['Address'], 
        'phone': row['Phone']
    })

labels_html = labels.render({'body': output})


# In[20]:


# Optional: Display the report here.
# import IPython
# IPython.display.HTML(orders_html)


# In[21]:


# Use Rapid API yakpdf - HTML to PDF to format the html output as pdf for printing.
import requests

def to_pdf(source_html):
    # Using https://rapidapi.com/yakpdf-yakpdf/api/yakpdf with limited free license.

    url = config.rapid_api_url

    payload = {
    	"source": { "html": source_html },
    	"pdf": {
    		"format": "Letter",
    		"scale": 1,
    		"printBackground": False
    	},
    	"wait": {
    		"for": "navigation",
    		"waitUntil": "load",
    		"timeout": 2500
    	}
    }
    headers = {
    	"content-type": "application/json",
    	"X-RapidAPI-Key": config.rapid_api_key,
    	"X-RapidAPI-Host": config.rapid_api_host
    }

    response = requests.post(url, json=payload, headers=headers)

    return response.content


# In[22]:


# Write out the files to print.

with open(order_pdf_file, 'wb') as f:
    f.write(to_pdf(orders_html))
print('Wrote {file}'.format(file = order_pdf_file))

with open(label_pdf_file, 'wb') as f:
    f.write(to_pdf(labels_html))
print('Wrote {file}'.format(file = label_pdf_file))

