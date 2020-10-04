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

    def _query_database(self, query):

        self._connection.ping()
        cursor = self._connection.cursor()

        cursor.execute(query)

        records = cursor.fetchall()

        cursor.close()
        # self._connection.close()

        return records

    def create_daily_plot(self):

        query = """
            SELECT * FROM `records` WHERE `user_id` LIKE {};
        """.format(self._user_id)
        records = self._query_database(query)

        query = """
            SELECT * FROM `goals` WHERE `user_id` LIKE {} LIMIT 1;
        """.format(self._user_id)
        goals = self._query_database(query)[0]
        start_date, end_date = goals[1], goals[2]
        start_miles, end_miles = goals[3], goals[4]

        df = pd.DataFrame(records)
        df.columns = ['user_id', 'date', 'time', 'miles']
        df['datetime'] = df['date'] + "T" + df['time']
        pd.to_datetime(df['datetime'])
        df.sort_values(by='datetime')

        data = [
            go.Scatter(
                x=df['datetime'],
                y=df['miles'],
            ),
            go.Scatter(
                x=[start_date, end_date],
                y=[start_miles, end_miles],
            ),
        ]

        return json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
