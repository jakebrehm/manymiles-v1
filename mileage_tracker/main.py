import configparser
import datetime
import os
import pathlib

import pymysql
from flask import Flask, flash, redirect, render_template, request, session
from flask_restful import Api, Resource, reqparse
from werkzeug.security import check_password_hash, generate_password_hash

import visualizations as vis


class Configuration:

    def __init__(self, config):
        self.config = configparser.ConfigParser()
        self.config.read(config)

    def get(self, environment_name, config_section, config_name):
        try:
            return os.environ[environment_name]
        except KeyError:
            return self.config.get(config_section, config_name)

PROJECT_FOLDER = pathlib.Path(__file__).resolve().parent.parent
CONFIG_LOCATION = os.path.join(PROJECT_FOLDER, 'data', 'config.ini')

config = Configuration(CONFIG_LOCATION)

server = Flask(__name__)
server.secret_key = os.urandom(24)

connection = pymysql.connect(
    host=config.get('CLEARDB_DATABASE_HOST', 'database', 'host'),
    user=config.get('CLEARDB_DATABASE_USER', 'database', 'user'),
    passwd=config.get('CLEARDB_DATABASE_PASSWORD', 'database', 'password'),
    database=config.get('CLEARDB_DATABASE_NAME', 'database', 'database'),
)

@server.route('/')
def login():

    session.modified = True

    if 'user_id' in session and 'username' in session:
        return redirect('/app')
    else:
        return render_template('login.html')

@server.route('/register')
def register():

    session.modified = True

    return render_template('register.html')

@server.route('/app')
def app():

    session.modified = True

    if 'user_id' in session and 'username' in session:

        connection.ping()
        cursor = connection.cursor()
        
        query = """
            SELECT * FROM `goals` WHERE `user_id` LIKE "{}" LIMIT 1;
        """.format(session['user_id'])
        cursor.execute(query)
        match = cursor.fetchall()

        goal = {
            'start_date': match[0][1] if match else None,
            'end_date': match[0][2] if match else None,
            'start_miles': match[0][3] if match else None,
            'end_miles': match[0][4] if match else None,
        }

        visualizer = vis.Visualizer(connection, session['user_id'])
        total_mileage_plot = visualizer.create_total_mileage_plot()
        daily_change_plot = visualizer.create_daily_change_plot()
        analysis = visualizer.perform_analysis()

        most_recent_record = visualizer.get_most_recent_record()
        most_recent_mileage = int(most_recent_record['miles'])

        cursor.close()
        connection.close()

        # TODO: Verify that current_time is timezone independent
        return render_template(
            'home.html',
            user=session['username'],
            goal=goal,
            total_mileage_plot=total_mileage_plot,
            daily_change_plot=daily_change_plot,
            analysis=analysis,
            most_recent_mileage=most_recent_mileage,
            current_time=datetime.datetime.now().strftime('%Y-%m-%dT%H:%M'),
        )
    else:
        return redirect('/')

@server.route('/login_validation', methods=['POST'])
def login_validation():

    session.modified = True

    username = request.form.get('username')
    password = request.form.get('password')

    connection.ping()
    cursor = connection.cursor()

    query = """
        SELECT * FROM `users` WHERE `username` LIKE "{}" LIMIT 1;
    """.format(username)
    cursor.execute(query)
    users = cursor.fetchall()

    if not users:
        cursor.close()
        connection.close()
        flash('No account seems to exist with that username.')
        return redirect('/')

    stored_password = users[0][2]

    passwords_match = check_password_hash(stored_password, password)

    cursor.close()
    connection.close()
    if passwords_match:
        session['user_id'] = users[0][0]
        session['username'] = users[0][1]
        return redirect('/app')
    else:
        flash('The password you entered does not match the one in our records.')
        return redirect('/')

@server.route('/add_user', methods=['POST'])
def add_user():

    session.modified = True

    username = request.form.get('add-username')
    password = request.form.get('add-password')
    hashed = generate_password_hash(password)

    connection.ping()
    cursor = connection.cursor()

    # 

    query = """
        SELECT * FROM `users` WHERE `username` LIKE "{}";
    """.format(username)
    cursor.execute(query)
    users = cursor.fetchall()

    if len(users):
        cursor.close()
        connection.close()
        flash('This username has already been taken.')
        return redirect('/register')

    #

    query = """
        INSERT INTO `users` (`id`, `username`, `password`)
        VALUES (NULL, "{}", "{}");
    """.format(username, hashed)
    cursor.execute(query)
    connection.commit()

    cursor.execute("""
        SELECT * FROM `users` WHERE `username` LIKE "{}"
    """.format(username))
    user = cursor.fetchall()
    session['user_id'] = user[0][0]
    session['username'] = user[0][1]
    cursor.close()
    connection.close()
    return redirect('/app')

@server.route('/logout')
def logout():

    session.modified = True

    if 'user_id' in session:
        session.pop('user_id')
        session.pop('username')
    return redirect('/')

@server.route('/update_goal', methods=['POST'])
def update_goal():

    session.modified = True

    start_miles = request.form.get('start-miles')
    start_date = request.form.get('start-date')
    end_miles = request.form.get('end-miles')
    end_date = request.form.get('end-date')

    connection.ping()
    cursor = connection.cursor()

    query = """
        REPLACE INTO `goals`
        (`user_id`, `start_date`, `end_date`, `start_miles`, `end_miles`)
        VALUES ("{}", "{}", "{}", "{}", "{}")
    """.format(session['user_id'], start_date, end_date, start_miles, end_miles)
    cursor.execute(query)
    connection.commit()

    cursor.close()
    connection.close()
    if session['user_id']:
        return redirect('/app')
    else:
        return redirect('/')

@server.route('/add_update_records', methods=['POST'])
def add_record():

    session.modified = True

    miles = request.form.get('miles')
    timedate = request.form.get('datetime')
    # view_records = request.form.get('view-records')
    add_record = request.form.get('add-record')

    if not miles or not timedate:
        return redirect('/app')

    if add_record is not None:
        date, time = timedate.split(r'T')

        connection.ping()
        cursor = connection.cursor()

        query = """
            INSERT INTO `records`
            (`user_id`, `date`, `time`, `miles`)
            VALUES ("{}", "{}", "{}", "{}")
        """.format(session['user_id'], date, time, miles)
        cursor.execute(query)
        connection.commit()

        cursor.close()
        connection.close()

        if session['user_id']:
            return redirect('/app')
        else:
            return redirect('/')
    
    else:
        return redirect('/records')

@server.route('/records')
def records():

    session.modified = True

    if 'user_id' in session and 'username' in session:

        connection.ping()
        cursor = connection.cursor()

        visualizer = vis.Visualizer(connection, session['user_id'])
        all_records = visualizer._records_df
        ids = all_records['id'].tolist()
        dates = all_records['date'].tolist()
        times = all_records['time'].tolist()
        miles = all_records['miles'].tolist()
        processed_records = zip(ids, dates, times, miles)

        cursor.close()
        connection.close()

        return render_template(
            'records.html',
            user=session['username'],
            records=processed_records,
        )
    else:
        return redirect('/')

@server.route('/update')
def update():

    session.modified = True

    if not 'user_id' in session:
        return redirect('/')
    
    record_id = int(request.args.get('record'))

    visualizer = vis.Visualizer(connection, session['user_id'])
    all_records = visualizer._records_df
    match = all_records[all_records['id'] == record_id]

    record = {
        'id': record_id,
        'miles': int(match['miles'].values[0]),
        'datetime': match['datetime'].values[0],
    }

    return render_template(
        'update.html',
        user=session['username'],
        record=record,
    )

@server.route('/update_record', methods=['POST'])
def update_record():

    session.modified = True

    if not 'user_id' in session:
        return redirect('/')

    record_id = request.args.get('record')

    connection.ping()
    cursor = connection.cursor()

    timedate = request.form.get('update-datetime')
    miles = request.form.get('update-miles')
    date, time = timedate.split(r'T')
    
    query = """
        UPDATE `records`
        SET `date` = "{}", `time` = "{}", `miles` = "{}"
        WHERE `user_id` LIKE "{}" AND `id` LIKE "{}";
    """.format(date, time, miles, session['user_id'], record_id)
    cursor.execute(query)
    connection.commit()

    cursor.close()
    connection.close()

    return redirect('/records')

@server.route('/delete_record', methods=['GET'])
def delete_record():

    session.modified = True

    if not 'user_id' in session:
        return redirect('/')

    record_id = request.args.get('record')

    connection.ping()
    cursor = connection.cursor()
    
    query = """
        DELETE FROM `records`
        WHERE `user_id` LIKE "{}" AND `id` LIKE "{}" LIMIT 1;
    """.format(session['user_id'], record_id)
    cursor.execute(query)
    connection.commit()

    cursor.close()
    connection.close()

    return redirect('/records')

api = Api(server)

class MostRecentRecordAPI(Resource):

    def get(self, username, password):

        if not username or not password:
            return {}

        connection.ping()
        cursor = connection.cursor()

        query = """
            SELECT * FROM `users` WHERE `username` LIKE "{}" LIMIT 1;
        """.format(username)
        cursor.execute(query)
        users = cursor.fetchall()

        user_id = users[0][0]
        stored_password = users[0][2]

        passwords_match = check_password_hash(stored_password, password)

        cursor.close()
        if passwords_match:
            session['user_id'] = users[0][0]
            session['username'] = users[0][1]

            visualizer = vis.Visualizer(connection, user_id)
            most_recent_record = visualizer.get_most_recent_record()

            connection.close()
            return {
                'date': str(most_recent_record['date'].values[0]),
                'time': str(most_recent_record['time'].values[0]),
                'miles': int(most_recent_record['miles']),
            }
        else:
            connection.close()
            return {}

api.add_resource(
    MostRecentRecordAPI,
    '/api/mostrecent/<string:username>&<string:password>'
)

add_record_put_args = reqparse.RequestParser()
add_record_put_args.add_argument('username', type=str, help='Username', required=True)
add_record_put_args.add_argument('password', type=str, help='Password', required=True)
add_record_put_args.add_argument('date', type=str, help='Date', required=False)
add_record_put_args.add_argument('time', type=str, help='Time', required=False)
add_record_put_args.add_argument('miles', type=str, help='Password', required=True)

class RecordAPI(Resource):

    def put(self):

        args = add_record_put_args.parse_args()

        username = args['username']
        password = args['password']
        miles = args['miles']

        timedate = datetime.datetime.now().strftime(r'%Y-%m-%dT%H:%M')
        parsed_date, parsed_time = timedate.split(r'T')
        date = args['date'] if args['date'] else parsed_date
        time = args['time'] if args['time'] else parsed_time

        connection.ping()
        cursor = connection.cursor()

        query = """
            SELECT * FROM `users` WHERE `username` LIKE "{}" LIMIT 1;
        """.format(username)
        cursor.execute(query)
        users = cursor.fetchall()

        user_id, stored_password = users[0][0], users[0][2]

        passwords_match = check_password_hash(stored_password, password)

        if passwords_match:

            query = """
                INSERT INTO `records`
                (`user_id`, `date`, `time`, `miles`)
                VALUES ("{}", "{}", "{}", "{}")
            """.format(user_id, date, time, miles)
            cursor.execute(query)
            connection.commit()

            cursor.close()
            connection.close()

            return args
        else:
            cursor.close()
            connection.close()
            return args

api.add_resource(
    RecordAPI,
    '/api/addrecord'
)

if __name__ == '__main__':
    server.run(debug=False)
