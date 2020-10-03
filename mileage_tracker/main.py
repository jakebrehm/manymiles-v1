import os
import pathlib
from configparser import ConfigParser

import pymysql
from flask import Flask, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash


PROJECT_FOLDER = pathlib.Path(__file__).resolve().parent
CONFIG_LOCATION = os.path.join(PROJECT_FOLDER, 'config.ini')
config = ConfigParser()
config.read(CONFIG_LOCATION)

server = Flask(__name__)
server.secret_key = os.urandom(24)

connection = pymysql.connect(
    host=config.get('database', 'host'),
    user=config.get('database', 'user'),
    passwd=config.get('database', 'password'),
    database=config.get('database', 'database'),
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

        cursor.close()
        connection.close()

        return render_template('home.html', user=session['username'], goal=goal)
    else:
        return redirect('/')

@server.route('/login_validation', methods=['POST'])
def login_validation():
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
    miles = request.form.get('miles')
    datetime = request.form.get('datetime')
    view_records = request.form.get('view-records')
    add_record = request.form.get('add-record')

    if not miles or not datetime:
        return redirect('/app')


    # return f'{datetime} --> {mileage}<br>View --> {view_records == None}<br>Add --> {add_record == None}'

    if add_record is not None:
        date, time = datetime.split('T')
            
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
        return redirect('/app')


if __name__ == '__main__':
    server.run(debug=True)
