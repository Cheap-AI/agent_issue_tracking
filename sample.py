employee - coming from rest api
changes - kafka
salary - file feed

I was given this data definitions and was told to write code that applies the changes to the employee table and join with the salary table. How woud you do it in python

import requests
import pandas
import boto3
from confluent_kafka import Consumer
import sqlalchemy

endpoint = "url"

employee = requests.get(endpoint)

employee_body = employee.body

employee_data = pandas.read_json(employee_body)

employee_data.

consumer = Consumer()




db = sqlalchemy.get_db(connection="")

db.execute("")


