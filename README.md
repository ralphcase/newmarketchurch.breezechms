# newmarketchurch.breezechms
Tools useful for the Newmarket Community Church and Food Pantry

[Newmarket Community Church](https://www.newmarketchurch.org/) uses [Breeze](https://www.breezechms.com/) to manage people and events.

One of the main missions of the church is the Food Pantry. See the [Food Pantry Operations Manual](https://static1.squarespace.com/static/62b9e0e5df408d5c55fc56c8/t/64ffa76bf37f8b502e50fc7a/1694476141825/Food+Pantry+Operations+Manual+_First+Edition+August+30+2023.docx+-+Google+Docs.pdf).

Panty documents are on [Google Drive](https://drive.google.com/drive/folders/0AF3bQjKDDPR-Uk9PVA). 

## To use these tools
These scripts use Python. Python virtual environments are recommended. See https://docs.python.org/3/tutorial/venv.html.

I like virtualenvwrapper to make it easier to work with virtual environments. See https://pypi.org/project/virtualenvwrapper-win/.

Development and use has been done with Jupyter Lab. See https://jupyter.org/install for installation instructions.

The scripts use pandas dataframes to work with the data. See https://pandas.pydata.org/.

Jinja2 is used to create html output for printing and reporting. See https://pypi.org/project/Jinja2/.

Printing from html with css is dependent on the OS and browser. I couldn't find any combination that works correctly for all the cases we need.
Instead, we convert the html to pdf, which can be reliably printed.
This depends on **Rapid API** yakpdf - HTML to PDF to format the html output as pdf for printing.
https://rapidapi.com/yakpdf-yakpdf/api/yakpdf with limited free license that allows the level of service we need for the weekly printing.

I'm looking at building the scripts to run under [docker](https://www.docker.com/) so they can be better run in different environments. This is a project still under development.

https://github.com/dawillcox/pyBreezeChMS - A Python wrapper for the Breeze API is used to simplify working with https://app.breezechms.com/api. 
