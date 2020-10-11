import json

import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go


class Visualizer:

    def __init__(self, connection, user_id):

        # Store the parameters
        self._connection = connection
        self._user_id = user_id

        # Initialize other parameters
        self._all_records_df = self._get_all_records()
        self._goals = self._get_goals()
        self._daily_mileage = self._determine_daily_mileage()
        self._optimal_miles_df = self._determine_optimal_miles()
        self._most_recent_record = self._get_most_recent_record()

    @property
    def all_records(self):
        return self._all_records_df

    @property
    def goals(self):
        return self._goals
    
    @property
    def optimal_miles(self):
        return self._optimal_miles_df
    
    @property
    def daily_mileage(self):
        return self._daily_mileage
    
    @property
    def most_recent_record(self):
        return self._most_recent_record
    
    @property
    def most_recent_mileage(self):
        most_recent_mileage = self._get_most_recent_mileage()
        # return int(most_recent_mileage['miles']) if most_recent_mileage else None
        return int(most_recent_mileage) if most_recent_mileage else None

    def get_goal_as_dict(self):

        # 
        goals = self.goals.copy()

        # 
        null = self._is_null(goals)

        # 
        return {
            'start_date': goals['start_date'].values[0] if not null else None,
            'end_date': goals['end_date'].values[0] if not null else None,
            'start_miles': goals['start_miles'].values[0] if not null else None,
            'end_miles': goals['end_miles'].values[0] if not null else None,
        }

    def perform_analysis(self):

        #
        analysis = {
            'valid': False,
            'budget': None,
            'daily': None,
            'overage': None,
            'over-under': None,
        }

        # 
        goals = self.goals.copy()
        optimal_miles = self._get_optimal_mileage_on_date()
        actual_miles = self._get_most_recent_mileage()

        #
        items = [goals, optimal_miles, actual_miles]
        if any(self._is_null(item) for item in items):
            return analysis
        # 
        analysis['valid'] = True

        # Note the start and end mileages of the user's goal
        start_miles = goals['start_miles'].values[0]
        end_miles = goals['end_miles'].values[0]
        analysis['budget'] = end_miles - start_miles

        # 
        overage = optimal_miles - actual_miles
        analysis['overage'] = f'{abs(overage):0.2f}'
        analysis['over-under'] = 'under' if overage >= 0 else 'over'

        # 
        analysis['daily'] = f'{self.daily_mileage:0.2f}'
        return analysis

    def create_total_mileage_plot(self):

        # 
        optimal_to_most_recent_date = self._get_optimal_mileages_to_date()

        # 
        if self._is_null(optimal_to_most_recent_date):
            return None

        # 
        data = [
            go.Scatter(
                x=self.all_records['datetime'],
                y=self.all_records['miles'],
                name='Actual',
                hovertemplate='<b>%{x}</b><br>%{y:0.2f} miles'
            ),
            go.Scatter(
                x=optimal_to_most_recent_date['date'],
                y=optimal_to_most_recent_date['miles'],
                fill='tonexty',
                line_color='green',
                name='Optimal',
                hovertemplate='<b>%{x}</b><br>%{y:0.2f} miles'
            ),
        ]

        # 
        return json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    def create_daily_change_plot(self):
        
        # 
        if self._is_null(self.all_records):
            return None

        # 
        records = self.all_records.copy()
        records.index = records['datetime']

        #
        records = records.groupby(pd.Grouper(freq='D')).max()

        # 
        differences = pd.DataFrame()
        differences['miles'] = records['miles'].diff()

        # 
        data = [
            go.Scatter(
                x=differences.index,
                y=differences['miles'],
                name='Change',
                hovertemplate='<b>%{x}</b><br>%{y:0.2f} mile change from previous day'
            ),
            go.Scatter(
                x=differences.index,
                y=[self.daily_mileage] * len(differences.index),
                line_color='red',
                name='Daily Allowance',
                opacity=0.25,
            ),
        ]

        # 
        return json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    def _query_database(self, query):

        # Ping the connection to wake it and create a cursor
        self._connection.ping()
        cursor = self._connection.cursor()
        # Execute the query and fetch the results
        cursor.execute(query)
        results = cursor.fetchall()
        # Close the cursor and connection
        cursor.close()
        # self._connection.close()
        # Return the results
        return results
    
    def _is_null(self, item):

        # 
        return item.empty if isinstance(item, pd.DataFrame) else not item

    def _get_all_records(self):

        # Query the database for all of the user's records
        query = """
            SELECT * FROM `records` WHERE `user_id` LIKE {};
        """.format(self._user_id)
        records = self._query_database(query)
        
        # Return if the user has no records
        if self._is_null(records):
            return pd.DataFrame()
        
        # If the user has records, create a DataFrame from the records
        column_names = ['id', 'user_id', 'date', 'time', 'miles']
        df = pd.DataFrame(records, columns=column_names)
        df['datetime'] = pd.to_datetime(df['date'] + 'T' + df['time'])
        df.sort_values(by='datetime')
        return df

    def _get_goals(self):

        # Query the database for the user's goal
        query = """
            SELECT * FROM `goals` WHERE `user_id` LIKE {} LIMIT 1;
        """.format(self._user_id)
        result = self._query_database(query)
        
        # Return if the user has no goal
        if self._is_null(result):
            return pd.DataFrame()

        # If the user has a goal, create a DataFrame of that information
        goals = result
        column_names = [
            'user_id', 'start_date', 'end_date', 'start_miles', 'end_miles',
        ]
        return pd.DataFrame(goals, columns=column_names)

    def _determine_daily_mileage(self):

        # Return if the user has no goal
        if self._is_null(self.goals):
            return None

        # Make a copy of the user's goal dataframe
        goals = self.goals.copy()

        # Note the start and end mileages of the user's goal
        start_miles = goals['start_miles'].values[0]
        end_miles = goals['end_miles'].values[0]

        # Convert the start date column to a datetime
        goals['start_date'] = pd.to_datetime(goals['start_date'], format=r'%Y-%m-%d')
        # Convert the end date column to a datetime
        goals['end_date'] = pd.to_datetime(goals['end_date'], format=r'%Y-%m-%d')
        # Determine the number of days the goal takes place over
        days = (goals['end_date'] - goals['start_date']).dt.days.values[0]

        # Return the daily mileage
        return (end_miles - start_miles) / (days + 1)

    def _determine_optimal_miles(self):
        
        # Return if the user has no goal
        if self._is_null(self.goals):
            return pd.DataFrame()
        
        # 
        goals = self.goals.copy()
        start_date = goals['start_date'].values[0]
        end_date = goals['end_date'].values[0]
        start_miles = goals['start_miles'].values[0]
        end_miles = goals['end_miles'].values[0]

        # 
        optimal_dates = [start_date, end_date]
        optimal_miles = [start_miles, end_miles]
        # 
        dates = pd.period_range(min(optimal_dates), max(optimal_dates))
        dates = dates.strftime(r'%Y-%m-%d').tolist()
        miles = [None] * len(dates)
        miles[0] = optimal_miles[0] + self.daily_mileage
        miles[-1] = optimal_miles[-1]
        # 
        optimal = pd.DataFrame(zip(dates, miles), columns=['date', 'miles'])
        optimal['miles'] = optimal['miles'].interpolate()
        optimal['datetime'] = pd.to_datetime(
            optimal['date'] + 'T11:59',
            format=r'%Y-%m-%dT%H:%M',
        )

        # 
        return optimal

    def _get_optimal_mileage_on_date(self, date='most recent'):

        # 
        if self._is_null(self.all_records) or self._is_null(self.optimal_miles):
            return None

        # 
        records = self.all_records.copy()
        optimal = self.optimal_miles.copy()

        # 
        if date == 'most recent':
            date = max(records['datetime'])

        # 
        return optimal[optimal['datetime'].dt.date == date.date()]['miles'].values[0]

    def _get_optimal_mileages_to_date(self, date=None):

        # Return an empty DataFrame in order to avoid an error
        if self._is_null(self.all_records) or self._is_null(self.optimal_miles):
            return pd.DataFrame()
        
        # Make copies of the appropriate dataframes
        records = self.all_records.copy()
        optimal = self.optimal_miles.copy()

        # By default, use the date of the most recent record
        if not date:
            date = max(records['datetime']).date()
        
        # Return the appropriate records
        return optimal[optimal['datetime'].dt.date <= date]

    def _get_most_recent_record(self):

        # 
        if self._is_null(self.all_records):
            return None

        #
        records = self.all_records.copy()
        return records[records['datetime'] == max(records['datetime'])]

    def _get_most_recent_mileage(self):

        # 
        most_recent_record = self._get_most_recent_record()

        # 
        if self._is_null(most_recent_record):
            return None
        
        # 
        return most_recent_record['miles'].values[0]