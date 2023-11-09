# newmarketchurch.breezechms
Tools useful for the Newmarket Community Church and Food Pantry

[Newmarket Community Church](https://www.newmarketchurch.org/) uses [Breeze](https://www.breezechms.com/) to manage people and events.

One of the main missions of the church is the Food Pantry. See the [Food Pantry Operations Manual](https://static1.squarespace.com/static/62b9e0e5df408d5c55fc56c8/t/64ffa76bf37f8b502e50fc7a/1694476141825/Food+Pantry+Operations+Manual+_First+Edition+August+30+2023.docx+-+Google+Docs.pdf).

Panty documents are on [Goole Drive](https://drive.google.com/drive/folders/0AF3bQjKDDPR-Uk9PVA). 

## To use these tools
These scripts use Python. Python virtual environments are recommended. See https://docs.python.org/3/tutorial/venv.html.

I like virtualenvwrapper to make it easier to work with virtual environments. See https://pypi.org/project/virtualenvwrapper-win/.

Development and use has been done with Jupiter Lab. See https://jupyter.org/install for installation instructions.

The scripts use pandas dataframes to work with the data. See https://pandas.pydata.org/.

Jinja2 is used to create html output for printing and reporting. See https://pypi.org/project/Jinja2/.

I've used [pdfkit](https://pypi.org/project/pdfkit/), which depends on [wkhtmltopdf](https://wkhtmltopdf.org/), to get print files. I'm not happy with this, both because it doesn't seem to work well and it makes the dependencies more complex.
