
This file collects some notes and examples that I thought might be valuable as I learn about the Breeze API.

Find the event for this week's shopping event.
`https://yoursubdomain.breezechms.com/api/events/attendance/add`

The Python wrapper suggested in https://app.breezechms.com/api seems to have major problems and no support.
I'm trying [https://pypi.org/project/breeze-chms-api/]
`from breeze_chms_api import breeze`

Initialize API 
'breeze_api = breeze.breeze_api(breeze_url='https://newmarketchurch.breezechms.com',
                               api_key='8dfd0a0d7f5aaec745a73542f58eb8ba')`

Get all the people
`
people = breeze_api.list_people()
display(len(people))
`

Find the shopping event by name and date.
`
events = breeze_api.list_events(start=title_date, end=title_date)
shoppingevent = [e for e in events if e['name'] == 'Food Pantry'][0]
display(shoppingevent)
`
Get the checked-in shoppers for the shoppingevent.
`
shoppers = breeze_api.list_attendance(instance_id=shoppingevent['id'])
display(shoppers)
`

https://yoursubdomain.breezechms.com/api/events/attendance/list?instance_id=1521321&type=person
