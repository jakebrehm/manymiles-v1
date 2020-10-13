import io
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
        self._all_records = self._get_all_records()
        self._goals = self._get_goals()
        self._daily_mileage = self._determine_daily_mileage()
        self._optimal_miles = self._determine_optimal_miles()
        self._most_recent_record = self._get_most_recent_record()

    @property
    def all_records(self):
        return self._all_records

    @property
    def goals(self):
        return self._goals
    
    @property
    def optimal_miles(self):
        return self._optimal_miles
    
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

        if not self._is_null(goals):
            # 
            analysis['valid'] = True

            # Note the start and end mileages of the user's goal
            start_miles = goals['start_miles'].values[0]
            end_miles = goals['end_miles'].values[0]
            analysis['budget'] = end_miles - start_miles

            # 
            analysis['daily'] = f'{self.daily_mileage:0.2f}'

            # Secondary requirement for overage and under-over
            requirements = [optimal_miles, actual_miles]
            if not any(self._is_null(item) for item in requirements):
                # 
                overage = optimal_miles - actual_miles
                analysis['overage'] = f'{abs(overage):0.2f}'
                analysis['over-under'] = 'under' if overage >= 0 else 'over'
        
        # 
        return analysis

    def create_total_mileage_plot(self):

        # 
        all_records = self.all_records.copy()
        optimal = self._get_optimal_mileages_to_date()

        # 
        if self._is_null(optimal):
            return None

        # Return None until there are at least two records
        if len(all_records) < 2:
            return None
        
        # 
        all_records['date'] = pd.to_datetime(all_records['date'], format=r'%Y-%m-%d')

        # 
        all_records.index = all_records['datetime']
        all_records = all_records.groupby(pd.Grouper(freq='D')).max()

        # Fill in missing dates with the previously recorded value
        all_records['miles'] = all_records['miles'].fillna(method='ffill')

        # 
        date = min(all_records['datetime']).date()
        optimal = optimal[optimal['datetime'].dt.date >= date]

        # 
        data = [
            go.Scatter(
                x=all_records.index,
                y=all_records['miles'],
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

        # Fill in missing dates with the previously recorded value
        records['miles'] = records['miles'].fillna(method='ffill')

        # 
        differences = pd.DataFrame()
        differences['change'] = records['miles'].diff()
        # The first row of a difference will always be NaN; change to zero
        differences['change'].iloc[0] = 0

        # Return None if there is less than two data points
        if len(differences) < 2:
            return None

        # Return None until there are at least two records
        if self._is_null(differences) or differences['change'].isnull().all():
            return None

        # 
        data = [
            go.Scatter(
                x=differences.index,
                y=differences['change'],
                name='Change',
                hovertemplate='<b>%{x}</b><br>%{y:0.2f} mile change'
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
    
    def records_to_csv(self, file_handle=None):

        # 
        if self._is_null(self.all_records):
            return None

        # 
        records = self.all_records.copy()[['date', 'time', 'miles']]

        # 
        output = io.StringIO()

        # 
        records.to_csv(output, sep=',', encoding='utf-8', index=False)
        contents = output.getvalue()

        # 
        output.close()

        # 
        return contents

    def _is_null(self, item):

        # 
        return item.empty if isinstance(item, pd.DataFrame) else not item

    def _get_all_records(self):

        # Query the database for all of the user's records
        query = """
            SELECT * FROM `records` WHERE `user_id` LIKE {};
        """.format(self._user_id)
        records = self._connection.fetch(query)
        
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
        result = self._connection.fetch(query)
        
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