# import datetime.datetime as dt
# import datetime
import json

import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go

class Visualizer:

    def __init__(self, connection, user_id):

        self._connection = connection
        self._user_id = user_id

        query = """
            SELECT * FROM `records` WHERE `user_id` LIKE {};
        """.format(self._user_id)
        self._records = self._query_database(query)

        df = pd.DataFrame(self._records)
        df.columns = ['user_id', 'date', 'time', 'miles']
        df['datetime'] = df['date'] + "T" + df['time']
        pd.to_datetime(df['datetime'])
        df.sort_values(by='datetime')
        self._records_df = df

        query = """
            SELECT * FROM `goals` WHERE `user_id` LIKE {} LIMIT 1;
        """.format(self._user_id)
        self._goals = self._query_database(query)[0]

        start_date, end_date = self._goals[1], self._goals[2]
        start_miles, end_miles = self._goals[3], self._goals[4]

        optimal_dates = [start_date, end_date]
        optimal_miles = [start_miles, end_miles]
        
        dates = pd.period_range(min(optimal_dates), max(optimal_dates))
        dates = dates.strftime(r'%Y-%m-%dT11:59').tolist()
        miles = [None] * len(dates)
        miles[0], miles[-1] = optimal_miles[0], optimal_miles[-1]

        optimal = pd.DataFrame(zip(dates, miles), columns=['date', 'miles'])
        optimal['miles'] = optimal['miles'].interpolate()
        pd.to_datetime(optimal['date'])

        self._daily_mileage = (end_miles - start_miles) / (len(optimal)-1)
        optimal['miles'] += self._daily_mileage

        self._optimal_df = optimal

    def _query_database(self, query):

        self._connection.ping()
        cursor = self._connection.cursor()

        cursor.execute(query)

        records = cursor.fetchall()

        cursor.close()
        # self._connection.close()

        return records

    def _get_optimal_mileages(self):
        optimal = self._optimal_df.copy()
        return optimal[optimal['date'] <= max(self._records_df['datetime'])]

    def _get_current_optimal_mileage(self):
        optimal = self._get_optimal_mileages()
        return optimal[optimal['date'] == max(optimal['date'])]['miles']

    def _get_most_recent_mileage(self):
        return self.get_most_recent_record()['miles']

    def get_most_recent_record(self):
        actual = self._records_df.copy()
        return actual[actual['datetime'] == max(actual['datetime'])]

    def perform_analysis(self):
        start_miles, end_miles = self._goals[3], self._goals[4]

        optimal_miles = self._get_current_optimal_mileage()
        actual_miles = self._get_most_recent_mileage()

        overage = optimal_miles.values[0] - actual_miles.values[0]

        return {
            'budget': end_miles - start_miles,
            'daily': f'{self._daily_mileage:0.2f}',
            'overage': f'{abs(overage):0.2f}',
            'over-under': 'under' if overage >= 0 else 'over',
        }

    def create_total_mileage_plot(self):

        optimal = self._get_optimal_mileages()

        data = [
            go.Scatter(
                x=self._records_df['datetime'],
                y=self._records_df['miles'],
                name='Actual',
                hovertemplate='<b>%{x}</b><br>%{y:0.2f} miles'
            ),
            go.Scatter(
                x=optimal['date'],
                y=optimal['miles'],
                fill='tonexty',
                line_color='green',
                name='Optimal',
                hovertemplate='<b>%{x}</b><br>%{y:0.2f} miles'
            ),
        ]

        return json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    def create_daily_change_plot(self):
        
        records = self._records_df.copy()
        records['datetime'] = pd.to_datetime(records['datetime'])
        records.index = records['datetime']
        records = records.groupby(pd.Grouper(freq='D')).max()

        differences = pd.DataFrame()
        differences['miles'] = records['miles'].diff()

        data = [
            go.Scatter(
                x=differences.index,
                y=differences['miles'],
                name='Change',
                hovertemplate='<b>%{x}</b><br>%{y:0.2f} mile change from previous day'
            ),
            go.Scatter(
                x=differences.index,
                y=[self._daily_mileage] * len(differences.index),
                line_color='red',
                name='Daily Allowance',
                opacity=0.25,
            ),
        ]

        return json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
