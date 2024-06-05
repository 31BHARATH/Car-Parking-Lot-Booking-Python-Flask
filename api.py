from flask import Blueprint, request, jsonify, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

api = Blueprint('api', __name__)

db_config = {
    'user': 'root',
    'password': 'admin@123',
    'host': 'localhost',
    'database': 'CarParking'
}

def redirect_if_logged_in(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            return jsonify({'message': 'Already logged in'}), 400
        return f(*args, **kwargs)
    return decorated_function

@api.route('/register', methods=['POST'])
@redirect_if_logged_in
def api_register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    vehicle_type = data.get('type')
    vehicle_model = data.get('model')
    vehicle_make = data.get('make')
    registration_number = data.get('reg')
    password = data.get('pass')
    confirm_password = data.get('retype')

    if password != confirm_password:
        return jsonify(message="Passwords do not match"), 400

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        return jsonify(message="Email already exists"), 400

    cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
    if cursor.fetchone():
        return jsonify(message="Phone number already exists"), 400

    cursor.execute("SELECT id FROM users WHERE registration_number = %s", (registration_number,))
    if cursor.fetchone():
        return jsonify(message="Registration number already exists"), 400

    hashed_password = generate_password_hash(password)
    try:
        cursor.execute("""
            INSERT INTO users (name, email, phone, vehicle_type, vehicle_model, vehicle_make, registration_number, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, email, phone, vehicle_type, vehicle_model, vehicle_make, registration_number, hashed_password))
        conn.commit()
        return jsonify(message="Registration successful"), 200
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify(message=f"Error: {err}"), 500
    finally:
        cursor.close()
        conn.close()

@api.route('/login', methods=['POST'])
@redirect_if_logged_in
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid input'}), 400

    email_or_phone = data.get('emailorphone')
    password = data.get('password')

    if not email_or_phone or not password:
        return jsonify({'error': 'Email/Phone and Password required'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s OR phone = %s", (email_or_phone, email_or_phone))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']

            cursor.execute("SELECT * FROM slots WHERE booked_by = %s", (user['id'],))
            user_slot = cursor.fetchone()

            if user_slot:
                return jsonify({'success': True, 'has_slot': True})

            cursor.execute("SELECT COUNT(1) AS available_count FROM slots WHERE is_available = 1")
            available_slots = cursor.fetchone()['available_count']

            if available_slots == 0:
                return jsonify({'success': True, 'has_slot': False, 'no_slots_message': "No slots available at the moment."})
            else:
                return jsonify({'success': True, 'has_slot': False})
        else:
            return jsonify({'error': 'Invalid email/phone or password'}), 401

    finally:
        cursor.close()
        conn.close()

@api.route('/slots', methods=['GET'])
def get_slots():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM slots")
    slots = cursor.fetchall()

    cursor.execute("SELECT id FROM slots WHERE booked_by = %s", (session['user_id'],))
    user_slot = cursor.fetchone()

    cursor.close()
    conn.close()

    user_slot_id = user_slot['id'] if user_slot else None
    return jsonify({'slots': slots, 'user_slot_id': user_slot_id})

@api.route('/reserve', methods=['POST'])
def reserve_slot():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    slot_id = request.json.get('slot_id')
    if not slot_id:
        return jsonify({'error': 'Slot ID is required'}), 400

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM slots WHERE id = %s", (slot_id,))
    slot = cursor.fetchone()

    if not slot:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Slot not found'}), 404

    if slot['booked_by']:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Slot is already booked'}), 400

    cursor.execute("SELECT id FROM slots WHERE booked_by = %s", (user_id,))
    already_booked_slot = cursor.fetchone()

    if already_booked_slot:
        cursor.close()
        conn.close()
        return jsonify({'error': "You have already booked a slot. Please release it before booking another one."}), 400

    check_in_time = datetime.now().strftime('%d/%m/%Y %I:%M:%S %p')

    cursor.execute("""
        UPDATE slots
        SET is_available = 0, booked_by = %s, check_in_time = %s
        WHERE id = %s
    """, (user_id, check_in_time, slot_id))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({'message': 'Slot reserved successfully'})

@api.route('/release', methods=['POST'])
def release_slot():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    slot_id = request.json.get('slot_id')
    if not slot_id:
        return jsonify({'error': 'Slot ID is required'}), 400

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM slots WHERE id = %s", (slot_id,))
    slot = cursor.fetchone()

    if not slot:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Slot not found'}), 404

    if slot['booked_by'] != user_id:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Slot is not booked by you'}), 400

    check_in_time = slot['check_in_time']
    check_out_time = datetime.now().strftime('%d/%m/%Y %I:%M:%S %p')

    cursor.execute("""
        UPDATE slots
        SET is_available = 1, booked_by = NULL, check_in_time = NULL
        WHERE id = %s AND booked_by = %s
    """, (slot_id, user_id))

    cursor.execute("""
        INSERT INTO bookings (user_id, slot_id, check_in_time, check_out_time)
        VALUES (%s, %s, %s, %s)
    """, (user_id, slot_id, check_in_time, check_out_time))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Slot released successfully'})

@api.route('/printbill', methods=['GET'])
def api_print_bill():
    user_id = session.get('user_id')
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT b.id, b.user_id, b.check_in_time, b.check_out_time, s.slot_name
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        WHERE b.user_id = %s
    """, (user_id,))
    bookings = cursor.fetchall()

    cursor.close()
    conn.close()

    if not bookings:
        return jsonify({'error': 'No bookings found'}), 404

    return jsonify({'bookings': bookings})
