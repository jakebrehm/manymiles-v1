import pymysql

import configuration as cfg


def connection_required(original):
    def wrapper(self, *args, **kwargs):
        if self.connection.open:
            self.connection.ping()
        else:
            self.connect()
            self.connection.ping()
        return original(self, *args, **kwargs)
    return wrapper


class Connection:

    def __init__(self, host, user, password, database):

        self._host = host
        self._user = user
        self._password = password
        self._database = database

        self.connect(host, user, password, database)

    @property
    def connection(self):

        # 
        if self.is_open:
            return self._connection
        else:
            return None
    
    @property
    def is_open(self):
        return self._connection.open

    def connect(self, host, user, password, database):

        # 
        self._connection = pymysql.connect(
            host=host,
            user=user,
            passwd=password,
            database=database,
        )

    def close(self):
        self.connection.close()

    @connection_required
    def fetch(self, query, commit=False):

        # Create a cursor
        cursor = self.connection.cursor()
        # Execute the query and fetch the results
        cursor.execute(query)
        results = cursor.fetchall()
        # Close the cursor and connection
        cursor.close()
        # Commit the changes if necessary
        if commit:
            self.connection.commit()
            return None
        # Return the results
        return results

    @connection_required
    def execute(self, query):
        self.fetch(query, commit=True)