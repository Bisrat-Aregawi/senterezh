#!/usr/bin/env python3
"""Module defines a flask app
"""
from flask import (
    Flask,
    flash,
    render_template,
    redirect,
    request,
    url_for
)
from flask_socketio import SocketIO, emit, join_room
from uuid import uuid4
from copy import deepcopy
from models import storage
import bcrypt
from models.user import User

app = Flask(__name__, static_url_path='/static')
secret_key = str(uuid4())
app.config['SECRET_KEY'] = secret_key
sio = SocketIO(app)

# Game session dictionary
rooms = {}


@app.route('/', methods=["GET", "POST"])
def home():
    """Respond to index page requests

    Redirect users if they want to play anonymouly
    """
    if request.method == "GET":
        return render_template('index.html')
    if request.method == "POST":
        # Capture the gameInterval data from client fetch request
        jsonData = request.get_json() or {}
        if rooms.get(jsonData.get('gameInterval')) is None:
            # Set a room id for the first player who requeted
            interval = jsonData.get('gameInterval')
            rooms[interval] = str(uuid4())
            room = rooms.get(interval)
        else:
            # Copy room name before deleting upon second player's request
            interval = jsonData.get('gameInterval')
            room = deepcopy(rooms[interval])
            del rooms[jsonData['gameInterval']]
        # Redirect clients to guest url with room in the path
        return redirect(
            '/guest/{:s}_{:s}'.format(interval, room), code=302
        )


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        user_name = request.form['user_name']
        password = request.form['password']
        age = request.form['age']
        email = request.form['email']
        usr = User()
        usr.first_name = first_name
        usr.last_name = last_name
        usr.user_name = user_name
        usr.password = bcrypt.hashpw(password.encode('utf-8'),
                                     bcrypt.gensalt())
        usr.email = email
        usr.age = age
        storage.new(usr)
        storage.save()
    return render_template('signup.html')


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        user_name = request.form['user_name']
        password = request.form['password']
        hashed_password = ""    # to be queried from database
        if not bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            flash('Incorrect password')
        else:
            redirect(url_for('index'))
    return render_template('signin.html')


@app.route('/guest/<room>')
def guest(room):
    """Render the guest gameplay page
    """
    return render_template('guest.html')


@sio.on('connect')
def on_connect():
    """Client connection listener
    """
    emit('connected', {'data': 'Socket is online'})


@sio.on('join')
def on_join(data: dict) -> None:
    """Client room connection listener

    Listens for socket event `join` comming from client and respond to a
    different event (`room joined`) upon successful join.

    Args:
        data: Data sent through socket upon a join request to room

    Returns:
        None
    """
    # Join to room requested by client
    join_room(data['room'])
    # Send board orientation to the client
    orientation = 'white'
    if rooms.get(data.get('gameInterval')) is None:
        orientation = 'black'
    emit(
        'room joined',
        {
            'ack': '{:s} joined room {:s}'.format(request.sid, data['room']),
            'orientation': orientation,
            'sid': request.sid
        },
        to=data['room']
    )


@sio.on('communicate')
def on_communicate(data):
    """Client chat exchange listener

    Listens for socket event `communicate` to respond to a room given in sent
    data. Responsible for exchanging chat data between clients in a room

    Args:
        data: Data sent through socket upon `fen exchange` event

    Returns:
        None
    """
    emit(
        'response',
        {'data': data['data'], 'sid': request.sid},
        to=data['room']
    )


@sio.on('fen exchange')
def on_exchange(data: dict) -> None:
    """Client fen string exchange listener

    Listens for socket event `fen exchange` to respond to a room given in sent
    json data.

    Args:
        data: Data sent through socket upon `fen exchange` event

    Returns:
        None
    """
    print(data)
    emit(
        'fen response',
        {'fenString': data['fenString'], 'sid': request.sid},
        to=data['room']
    )


if __name__ == "__main__":
    app.run(
        host='0.0.0.0',
        port=5000
    )
