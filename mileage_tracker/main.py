import os
import pathlib
from configparser import ConfigParser

import pymysql
from flask import Flask, render_template, request, redirect, session


PROJECT_FOLDER = pathlib.Path(__file__).resolve().parent
CONFIG_LOCATION = os.path.join(PROJECT_FOLDER, 'config.ini')
config = ConfigParser()
config.read(CONFIG_LOCATION)

app = Flask(__name__)
app.secret_key = os.urandom(24)

connection = pymysql.connect(
    host=config.get('database', 'host'),
    user=config.get('database', 'user'),
    passwd=config.get('database', 'password'),
    database=config.get('database', 'database'),
)
cursor = connection.cursor()

@app.route('/')
def login():
    if 'user_id' in session:
        return redirect('/home')
    else:
        return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/home')
def home():
    if 'user_id' in session:
        return render_template('home.html')
    else:
        return redirect('/')

@app.route('/login_validation', methods=['POST'])
def login_validation():
    email = request.form.get('email')
    password = request.form.get('password')

    query = """
        SELECT * FROM `users` WHERE `email` LIKE "{}" AND `password` LIKE "{}"
        LIMIT 1;
    """.format(email, password)
    cursor.execute(query)
    users = cursor.fetchall()

    if users:
        session['user_id'] = users[0][0]
        return redirect('/home')
    else:
        return redirect('/')

@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form.get('add-name')
    email = request.form.get('add-email')
    password = request.form.get('add-password')

    query = """
        INSERT INTO `users` (`id`, `name`, `email`, `password`)
        VALUES (NULL, "{}", "{}", "{}");
    """.format(name, email, password)
    cursor.execute(query)
    connection.commit()

    cursor.execute("""
        SELECT * FROM `users` WHERE `email` LIKE "{}"
    """.format(email))
    user = cursor.fetchall()
    session['user_id'] = user[0][0]
    return redirect('/home')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        session.pop('user_id')
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
