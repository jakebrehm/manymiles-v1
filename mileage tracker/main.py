import os
import pathlib
from configparser import ConfigParser

from flask import Flask, render_template, request
import mysql.connector

PROJECT_FOLDER = pathlib.Path(__file__).resolve().parent
CONFIG_LOCATION = os.path.join(PROJECT_FOLDER, 'config.ini')
config = ConfigParser()
config.read(CONFIG_LOCATION)

app = Flask(__name__)

conn = mysql.connector.connect(
    host=config.get('database', 'host'),
    user=config.get('database', 'user'),
    password=config.get('database', 'password'),
    database=config.get('database', 'database'),
)
cursor = conn.cursor()

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/login_validation', methods=['POST'])
def login_validation():
    email = request.form.get('email')
    password = request.form.get('password')

    query = """
        SELECT * FROM `users` WHERE `email` LIKE "{}" AND `password` LIKE "{}";
    """.format(email, password)
    cursor.execute(query)
    users = cursor.fetchall()

    if users:
        return render_template('home.html')
    else:
        return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)