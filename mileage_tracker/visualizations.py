# import datetime.datetime as dt
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

        query = """
            SELECT * FROM `goals` WHERE `user_id` LIKE {} LIMIT 1;
        """.format(self._user_id)
        self._goals = self._query_database(query)[0]

    def _query_database(self, query):

        self._connection.ping()
        cursor = self._connection.cursor()

        cursor.execute(query)

        records = cursor.fetchall()

        cursor.close()
        # self._connection.close()

        return records

    def create_daily_plot(self):
        
        start_date, end_date = self._goals[1], self._goals[2]
        start_miles, end_miles = self._goals[3], self._goals[4]

        df = pd.DataFrame(self._records)
        df.columns = ['user_id', 'date', 'time', 'miles']
        df['datetime'] = df['date'] + "T" + df['time']
        pd.to_datetime(df['datetime'])
        df.sort_values(by='datetime')

        optimal_dates = [start_date, end_date]
        optimal_miles = [start_miles, end_miles]
        names = ['date', 'miles']

        dates = pd.period_range(min(optimal_dates), max(optimal_dates))
        dates = dates.strftime(r'%Y-%m-%dT11:59').tolist()
        miles = [None] * len(dates)
        miles[0], miles[-1] = optimal_miles[0], optimal_miles[-1]

        optimal = pd.DataFrame(zip(dates, miles), columns=names)
        optimal['miles'] = optimal['miles'].interpolate()
        pd.to_datetime(optimal['date'])
        optimal = optimal[optimal['date'] <= max(df['datetime'])]

        data = [
            go.Scatter(
                x=df['datetime'],
                y=df['miles'],
                name = 'Actual',
            ),
            go.Scatter(
                x=optimal['date'],
                y=optimal['miles'],
                fill='tonexty',
                line_color='green',
                name = 'Optimal',
            ),
        ]

        return json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
