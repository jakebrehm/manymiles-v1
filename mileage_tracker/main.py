import datetime

from flask import Flask, flash, redirect, render_template, request, session, Response
from flask_restful import Api, Resource, reqparse
from werkzeug.security import check_password_hash, generate_password_hash

import configuration as cfg
import database as db
import visualizations as vis


config = cfg.Configuration()

server = Flask(__name__)
server.secret_key = config.get('SECRET_KEY', 'general', 'secret key')

connection = db.Connection(
    host=config.get('CLEARDB_DATABASE_HOST', 'database', 'host'),
    user=config.get('CLEARDB_DATABASE_USER', 'database', 'user'),
    password=config.get('CLEARDB_DATABASE_PASSWORD', 'database', 'password'),
    database=config.get('CLEARDB_DATABASE_NAME', 'database', 'database'),
)

@server.route('/')
def login():
    if 'user_id' in session and 'username' in session:
        return redirect('/app')
    else:
        return render_template('login.html')

@server.route('/register')
def register():
    return render_template('register.html')

@server.route('/app')
def app():
    if 'user_id' in session and 'username' in session:

        visualizer = vis.Visualizer(connection, session['user_id'])
        total_mileage_plot = visualizer.create_total_mileage_plot()
        daily_change_plot = visualizer.create_daily_change_plot()
        analysis = visualizer.perform_analysis()
        goal = visualizer.get_goal_as_dict()
        most_recent_mileage = visualizer.most_recent_mileage

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
    username = request.form.get('username')
    password = request.form.get('password')

    query = """
        SELECT * FROM `users` WHERE `username` LIKE "{}" LIMIT 1;
    """.format(username)
    users = connection.fetch(query)

    if not users:
        flash('No account seems to exist with that username.')
        return redirect('/')

    stored_password = users[0][2]

    passwords_match = check_password_hash(stored_password, password)

    if passwords_match:
        session['user_id'] = users[0][0]
        session['username'] = users[0][1]
        return redirect('/app')
    else:
        flash('The password you entered does not match the one in our records.')
        return redirect('/')

@server.route('/add_user', methods=['POST'])
def add_user():
    username = request.form.get('add-username')
    password = request.form.get('add-password')
    hashed = generate_password_hash(password)

    query = """
        SELECT * FROM `users` WHERE `username` LIKE "{}";
    """.format(username)
    users = connection.fetch(query)

    if len(users):
        flash('This username has already been taken.')
        return redirect('/register')

    query = """
        INSERT INTO `users` (`id`, `username`, `password`)
        VALUES (NULL, "{}", "{}");
    """.format(username, hashed)
    connection.execute(query)

    query = """
        SELECT * FROM `users` WHERE `username` LIKE "{}"
    """.format(username)
    user = connection.fetch(query)

    session['user_id'] = user[0][0]
    session['username'] = user[0][1]
    return redirect('/app')

@server.route('/logout')
def logout():
    if 'user_id' in session:
        session.pop('user_id')
        session.pop('username')
    return redirect('/')

@server.route('/update_goal', methods=['POST'])
def update_goal():
    start_miles = request.form.get('start-miles')
    start_date = request.form.get('start-date')
    end_miles = request.form.get('end-miles')
    end_date = request.form.get('end-date')

    query = """
        REPLACE INTO `goals`
        (`user_id`, `start_date`, `end_date`, `start_miles`, `end_miles`)
        VALUES ("{}", "{}", "{}", "{}", "{}")
    """.format(session['user_id'], start_date, end_date, start_miles, end_miles)
    connection.execute(query)

    if session['user_id']:
        return redirect('/app')
    else:
        return redirect('/')

@server.route('/add_update_records', methods=['POST'])
def add_record():
    miles = request.form.get('miles')
    timedate = request.form.get('datetime')
    view_records = request.form.get('view-records')
    add_record = request.form.get('add-record')

    if view_records:
        return redirect('/records')

    if add_record:

        if not miles or not timedate:
            return redirect('/app')
        
        date, time = timedate.split(r'T')

        query = """
            INSERT INTO `records`
            (`user_id`, `date`, `time`, `miles`)
            VALUES ("{}", "{}", "{}", "{}")
        """.format(session['user_id'], date, time, miles)
        connection.execute(query)

        if session['user_id']:
            return redirect('/app')
        else:
            return redirect('/')
    
    else:
        return redirect('/records')

@server.route('/records')
def records():
    if 'user_id' in session and 'username' in session:

        visualizer = vis.Visualizer(connection, session['user_id'])
        all_records = visualizer.all_records.iloc[::-1]
        if all_records.empty:
            processed_records = None
        else:
            ids = all_records['id'].tolist()
            dates = all_records['date'].tolist()
            times = all_records['time'].tolist()
            miles = all_records['miles'].tolist()
            processed_records = list(zip(ids, dates, times, miles))

        return render_template(
            'records.html',
            user=session['username'],
            records=processed_records,
        )
    else:
        return redirect('/')

@server.route('/update')
def update():
    if not 'user_id' in session:
        return redirect('/')
    
    record_id = int(request.args.get('record'))

    visualizer = vis.Visualizer(connection, session['user_id'])
    all_records = visualizer.all_records
    match = all_records[all_records['id'] == record_id]

    record = {
        'id': record_id,
        'miles': int(match['miles'].values[0]),
        'datetime': match['datetime'].dt.strftime(r'%Y-%m-%dT%H:%M').values[0],
    }

    return render_template(
        'update.html',
        user=session['username'],
        record=record,
    )

@server.route('/update_record', methods=['POST'])
def update_record():
    if not 'user_id' in session:
        return redirect('/')

    record_id = request.args.get('record')

    timedate = request.form.get('update-datetime')
    miles = request.form.get('update-miles')
    date, time = timedate.split(r'T')
    
    query = """
        UPDATE `records`
        SET `date` = "{}", `time` = "{}", `miles` = "{}"
        WHERE `user_id` LIKE "{}" AND `id` LIKE "{}";
    """.format(date, time, miles, session['user_id'], record_id)
    connection.execute(query)

    return redirect('/records')

@server.route('/delete_record', methods=['GET'])
def delete_record():
    if not 'user_id' in session:
        return redirect('/')

    record_id = request.args.get('record')
    
    query = """
        DELETE FROM `records`
        WHERE `user_id` LIKE "{}" AND `id` LIKE "{}" LIMIT 1;
    """.format(session['user_id'], record_id)
    connection.execute(query)

    return redirect('/records')

@server.route('/export')
def export():
    if not 'user_id' in session or not 'username' in session:
        return redirect('/')
    
    user = session['username']
    visualizer = vis.Visualizer(connection, session['user_id'])
    data = visualizer.records_to_csv()

    return Response(
        data,
        mimetype='text/csv',
        headers={
            'Content-disposition': f'attachment; filename=manymiles_{user}.csv',
        }
    )

@server.route('/change_password')
def change_password():
    if not 'user_id' in session:
        return redirect('/')
        
    return render_template(
        'change_password.html',
        user=session['username'],
    )

@server.route('/update_password', methods=['POST'])
def update_password():
    if not 'user_id' in session or not 'username' in session:
        return redirect('/')

    current_password = request.form.get('current-password')
    new_password = request.form.get('new-password')
    retyped_new_password = request.form.get('retype-new-password')

    query = """
        SELECT * FROM `users` WHERE `id` LIKE "{}" LIMIT 1;
    """.format(session['user_id'])
    users = connection.fetch(query)

    stored_password = users[0][2]
    passwords_match = check_password_hash(stored_password, current_password)

    if not all([current_password, new_password, retyped_new_password]):
        flash('Please make sure all fields are filled out.', 'danger')
        return redirect('/change_password')
    elif not passwords_match:
        flash(
            'The current password you entered does not match the one on file.',
            'danger',
        )
        return redirect('/change_password')
    elif new_password != retyped_new_password:
        flash('The new passwords must match.', 'danger')
        return redirect('/change_password')
    elif current_password == new_password:
        flash(
            'Your new password can not be the same as your current password.',
            'danger',
        )
        return redirect('/change_password')
    
    hashed_password = generate_password_hash(new_password)

    query = """
        UPDATE `users` SET `password` = "{}" WHERE `id` LIKE "{}";
    """.format(hashed_password, session['user_id'])
    connection.execute(query)

    flash('Password successfully updated.', 'success')
    return redirect('/change_password')

api = Api(server)

class MostRecentRecordAPI(Resource):

    def get(self, username, password):

        if not username or not password:
            return {}

        query = """
            SELECT * FROM `users` WHERE `username` LIKE "{}" LIMIT 1;
        """.format(username)
        users = connection.fetch(query)

        user_id = users[0][0]
        stored_password = users[0][2]

        passwords_match = check_password_hash(stored_password, password)

        if passwords_match:
            
            visualizer = vis.Visualizer(connection, user_id)
            most_recent_record = visualizer.most_recent_record

            return {
                'date': str(most_recent_record['date'].values[0]),
                'time': str(most_recent_record['time'].values[0]),
                'miles': int(most_recent_record['miles']),
            }
        else:
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

        query = """
            SELECT * FROM `users` WHERE `username` LIKE "{}" LIMIT 1;
        """.format(username)
        users = connection.fetch(query)

        user_id, stored_password = users[0][0], users[0][2]

        passwords_match = check_password_hash(stored_password, password)

        if passwords_match:

            query = """
                INSERT INTO `records`
                (`user_id`, `date`, `time`, `miles`)
                VALUES ("{}", "{}", "{}", "{}")
            """.format(user_id, date, time, miles)
            connection.execute(query)

            return args
        else:
            return args

api.add_resource(
    RecordAPI,
    '/api/addrecord'
)

class OverageAPI(Resource):

    def get(self, username, password):

        if not username or not password:
            return {}

        query = """
            SELECT * FROM `users` WHERE `username` LIKE "{}" LIMIT 1;
        """.format(username)
        users = connection.fetch(query)

        user_id = users[0][0]
        stored_password = users[0][2]

        passwords_match = check_password_hash(stored_password, password)

        if passwords_match:

            visualizer = vis.Visualizer(connection, user_id)
            analysis = visualizer.perform_analysis()

            return {
                'overage': float(analysis['overage']),
            }
        else:
            return {}

api.add_resource(
    OverageAPI,
    '/api/overage/<string:username>&<string:password>'
)

if __name__ == '__main__':
    server.run(debug=True)
