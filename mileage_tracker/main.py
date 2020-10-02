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
        return render_template('home.html', user=session['username'])
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
    return redirect('/app')

@server.route('/logout')
def logout():
    if 'user_id' in session:
        session.pop('user_id')
        session.pop('username')
    return redirect('/')

if __name__ == '__main__':
    server.run(debug=True)
