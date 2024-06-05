from flask import Flask, render_template, session, redirect, url_for, make_response
import mysql.connector
from functools import wraps

app = Flask(__name__)
app.secret_key = 'secret_key'

db_config = {
    'user': 'root',
    'password': 'admin@123',
    'host': 'localhost',
    'database': 'CarParking'
}

from api import api  

app.register_blueprint(api, url_prefix='/api') 

def redirect_if_logged_in(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            return redirect(url_for('slots'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET'])
@redirect_if_logged_in
def register():
    return render_template('register.html')

@app.route('/login', methods=['GET'])
@redirect_if_logged_in
def login_page():
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/slots')
def slots():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    return render_template('slots.html')

@app.route('/printbill', methods=['GET'])
def render_print_bill():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    return render_template('printbill.html')

@app.route('/bill/<int:booking_id>')
def render_bill(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT bookings.id AS booking_id, users.id AS user_id, users.name AS username,
               users.registration_number AS reg_number, bookings.check_in_time,
               bookings.check_out_time, slots.slot_name
        FROM bookings
        INNER JOIN users ON bookings.user_id = users.id
        INNER JOIN slots ON bookings.slot_id = slots.id
        WHERE bookings.id = %s
    """, (booking_id,))
    bill = cursor.fetchone()

    cursor.close()
    conn.close()

    if not bill:
        return "Bill not found", 404

    return render_template('bill.html', booking=bill)

if __name__ == '__main__':
    app.run(debug=True)
