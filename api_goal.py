import requests
import json
from datetime import datetime
from flask import request, url_for
from flask_api import FlaskAPI, status, exceptions
import pandas as pd
import numpy as np
from sklearn import datasets, linear_model
from sklearn.isotonic import IsotonicRegression
import os

base_url = "https://citizensbank.openbankproject.com/my/logins/direct"
password = os.environ['CITIZENSPASSWORD']
consumer_key = os.environ['CITIZENSAPIKEY']

def get_token(uri, password, key):
	login_header  = { 'Authorization' : 'DirectLogin username="%s",password="%s",consumer_key="%s"' % ("varshith", password, key)}
	r = requests.post(uri, headers=login_header)
	t = r.json()['token']
	return t


app = FlaskAPI(__name__)

import http.client
conn = http.client.HTTPSConnection("citizensbank.openbankproject.com")
headers = {
   'authorization': "DirectLogin token=\"eyJhbGciOiJIUzI1NiJ9.eyIiOiIifQ._WL1_alFDOjxXtmyWr2jE1Sx7nV3Ex-1fnB8HqFQknI\"",
   'cache-control': "no-cache",
   'postman-token': "bf1719b2-1f81-5611-0dbc-00e74745b834"
   }
conn.request("GET", "/obp/v4.0.0/my/banks/citizens.0201.us-b.cb/accounts/69b1fd57-c7df-4b22-ab2b-5f7cc6e73f70/account", headers=headers)
res = conn.getresponse()
data = res.read()

bank_id = "citizens.0201.us-b.cb"

conn.request("GET", "/obp/v4.0.0/banks", headers=headers)
res = conn.getresponse()
data = res.read()

headers = {
   'authorization': "DirectLogin token=\"%s\""%(get_token(base_url, password, consumer_key)),
   'cache-control': "no-cache",
   'postman-token': "bf1719b2-1f81-5611-0dbc-00e74745b834",
   'Content-Type' : "application/json"
   }

def get_transactions_for_account(account_id, bank_id, view_id="firehose"):
	uri = "/obp/v4.0.0/banks/{0}/firehose/accounts/{1}/views/{2}/transactions".format(bank_id, account_id, view_id)
	conn.request("GET", uri, headers=headers)
	res = conn.getresponse()
	data = res.read()
	return json.loads(data.decode("utf-8"))

def get_transaction(bank_id, account_id, transaction_id):
    uri = "/obp/v4.0.0/banks/{0}/accounts/{1}/firehose/transactions/{2}/transaction".format(bank_id, account_id, transaction_id)
    conn.request("GET", uri, headers=headers)
    res = con.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))

def get_transaction_amount(transaction):
	return float(transaction["details"]["value"]["amount"])

def is_transaction_debit(transaction):
	return get_transaction_amount(transaction) < 0

def is_transaction_credit(transaction):
	return get_transaction_amount(transaction) > 0


def get_account_ids(bank_id, view_id="firehose"):
	accounts = get_accounts_from_bank(bank_id, view_id)["accounts"]
	account_ids = []
	for account in accounts:
		account_ids.append(account["id"])
	return account_ids

def get_transaction_ids(transactions):
    ids = []
    for transaction in transactions:
        ids.append(transaction["id"])
    return ids    	

def get_accounts_from_bank(bank_id, view_id="firehose"):
	uri = "/obp/v4.0.0/banks/{0}/firehose/accounts/views/{1}".format(bank_id, view_id)
	conn.request("GET", uri, headers=headers)
	res = conn.getresponse()
	data = res.read()
	return json.loads(data.decode("utf-8"))

def get_transaction_description(transaction):
	return transaction["details"]["description"]

def get_transaction_type(transaction):
    return transaction["details"]["type"]

def get_transaction_posted_time_stamp(transaction):
    return transaction["details"]["posted"] 

def get_transaction_completed_time_stamp(transaction):
    return transaction["details"]["completed"]

def get_balance_after_transaction(transaction):
	return float(transaction["details"]["new_balance"]["amount"])


def get_transaction_amounts(transactions):
    amounts = []
    for transaction in transactions["transactions"]:
        amounts.append(get_transaction_amount(transaction))
    return amounts  

def get_transaction_descriptions(transactions):
	descriptions = []
	for transaction in transactions["transactions"]:
		descriptions.append(get_transaction_description(transaction))
	return descriptions	

def get_transaction_descriptions_for_account(account_id, bank_id, view_id="firehose"):
	transactions = get_transactions_for_account(account_id, bank_id, view_id)
	return get_transaction_descriptions(transactions)


def get_transaction_amounts_for_account(account_id, bank_id, view_id="firehose"):
	transactions = get_transactions_for_account(account_id, bank_id, view_id)
	return get_transaction_amounts(transactions)

def get_account_balances_at_transactional_points(transactions):
	balances = []
	for transaction in transactions["transactions"]:
		balances.append(get_balance_after_transaction(transaction))
	return balances	

def get_account_balances_at_transactional_points_for_account(account_id, bank_id, view_id="firehose"):
    transactions = get_transactions_for_account(account_id, bank_id, view_id)
    return get_account_balances_at_transactional_points(transactions)


def get_datetime_obj_from_str(datestring):
	return datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%SZ")


def get_time_range_of_transactions(account_id, bank_id, view_id="firehose"):
	transactions = get_transactions_for_account(account_id, bank_id, view_id)
	dates = []
	for transaction in transactions["transactions"]:
		print(get_transaction_completed_time_stamp(transaction))
		dates.append(get_transaction_completed_time_stamp(transaction))
	fromdate = get_transaction_completed_time_stamp(transactions["transactions"][-1])
	todate = get_transaction_completed_time_stamp(transactions["transactions"][0])
	print(len(dates))
	return get_datetime_obj_from_str(todate) - get_datetime_obj_from_str(fromdate)

def get_ordinal_dates_for_transactions(account_id, bank_id, view_id="firehose"):
	transactions = get_transactions_for_account(account_id, bank_id, view_id)
	ordinaldates = []
	for transaction in transactions["transactions"]:
		date = get_datetime_obj_from_str(get_transaction_completed_time_stamp(transaction))
		ordinaldates.append(date.date().toordinal())
	return ordinaldates	

def get_weights_for_transactions_descriptions(account_id, bank_id, view_id="firehose"):
	descriptions = get_transaction_descriptions_for_account(account_id, bank_id, view_id)
	total_descriptions_count = len(descriptions)
	description_count_map = {}
	for description in descriptions:
		if description in description_count_map:
			description_count_map[description] += 1
		else:
		    description_count_map[description] = 1
	description_stats = {}
	print(description_count_map)
	for description in description_count_map:
	    description_stats[description] = description_count_map[description]/total_descriptions_count

	return description_stats    

def get_day_balance_mapped_dataframe(account_id, bank_id, view_id="firehose"):
	balance_data = {'ordinaldate': list(reversed(get_ordinal_dates_for_transactions(account_id, bank_id, view_id))), 'balance':list(reversed(get_account_balances_at_transactional_points_for_account(account_id, bank_id, view_id)))}
	df = pd.DataFrame.from_dict(balance_data)
	return df

def fit_linear_regressor_for_balances(df):
	Y = df["balance"]
	X = df["ordinaldate"]
	Y = Y.values.reshape(len(Y),1)
	print (Y)
	X = X.values.reshape(len(X),1)
	print(X)
	regr = linear_model.LinearRegression()
	model = regr.fit(X,Y)
	intercept = model.intercept_
	slope = model.coef_
	#Y = slope*(X) + intercept
	return model


def fit_isotonic_regressor_for_balances(df):
	Y = df["balance"]
	X = df["ordinaldate"]
	Y = Y.values.reshape(len(Y), 1)
	X = X.values.reshape(len(X), 1)
	regr = IsotonicRegression()
	model =regr.fit_transform(X,Y)
	return model

def determine_goal_date(goal_amount, account_id, bank_id, view_id="firehose"):
	df = get_day_balance_mapped_dataframe(account_id, bank_id, view_id)
	model = fit_linear_regressor_for_balances(df)
	intercept = model.intercept_
	slope = model.coef_
	ordinal_goal_date = (goal_amount-intercept)/slope
	print(ordinal_goal_date)
	dto = datetime.fromordinal(ordinal_goal_date)
	return str(dto)

@app.route("/", methods=['POST'])
def get_goal_date():
	goal_amount = str(request.data.get('amount', ''))
	account_id = str(request.data.get('id', ''))
	goal_date = determine_goal_date(float(goal_amount), get_account_ids(bank_id)[int(account_id)], bank_id)
	return {'predicted_goal_date': goal_date}

@app.route("/stats", methods=['POST'])
def get_transaction_stats():
	account_id = str(request.data.get('id', ''))
	stats = get_weights_for_transactions_descriptions(get_account_ids(bank_id)[int(account_id)], bank_id)
	return {'transaction_metrics':stats}

if __name__ == "__main__":
    app.run()