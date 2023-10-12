from flask import Flask, render_template, request, jsonify, redirect, url_for
import qrcode
import io
import base64
from PIL import Image
from pyzbar.pyzbar import decode
import mysql.connector

app = Flask(__name__)

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'
USER_USERNAME = 'user'
USER_PASSWORD = 'user'

admin_logged_in = False
user_logged_in = False

db_config = {
 #   'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'info'
}

db_conn = mysql.connector.connect(**db_config)
db_cursor = db_conn.cursor()

create_table_query = """
CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    rollno VARCHAR(10),
    student_id VARCHAR(10)
)
"""
db_cursor.execute(create_table_query)

@app.route('/')
def index():
    return render_template('user_login.html', admin_logged_in=admin_logged_in, user_logged_in=user_logged_in)

@app.route('/generate_qr', methods=['GET', 'POST'])
def generate_qr():
    if not admin_logged_in:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form['name']
        rollno = request.form['rollno']
        student_id = request.form['id']

        data = f"Name: {name}\nRoll No: {rollno}\nID: {student_id}"
        qr = qrcode.make(data)
        buffered = io.BytesIO()
        qr.save(buffered, format='PNG')
        qr_image_base64 = base64.b64encode(buffered.getvalue()).decode()

        insert_query = "INSERT INTO students (name, rollno, student_id) VALUES (%s, %s, %s)"
        insert_data = (name, rollno, student_id)

        db_cursor.execute(insert_query, insert_data)
        db_conn.commit()

        return render_template('index.html', qr_image_base64=qr_image_base64, admin_logged_in=admin_logged_in, user_logged_in=user_logged_in)

    return render_template('index.html', admin_logged_in=admin_logged_in, user_logged_in=user_logged_in)

@app.route('/scan_qr')
def scan_qr():
    if not user_logged_in:
        return redirect(url_for('user_login'))
    
    return render_template('scanner.html', user_logged_in=user_logged_in)

@app.route('/decode_qr', methods=['POST'])
def decode_qr():
    if not user_logged_in:
        return jsonify({'scannedData': 'Authentication required.'})
    
    image_data = request.form['image_data']
    image_data = image_data.replace('data:image/png;base64,', '')

    with io.BytesIO(base64.b64decode(image_data)) as img_buffer:
        img = Image.open(img_buffer)
        qr_codes = decode(img)

        if qr_codes:
            data = qr_codes[0].data.decode('utf-8')
            return jsonify({'scannedData': data})
        else:
            return jsonify({'scannedData': 'QR code not detected.'})

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    global admin_logged_in
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            admin_logged_in = True
            return redirect(url_for('generate_qr'))
    return render_template('admin_login.html')

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    global user_logged_in
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USER_USERNAME and password == USER_PASSWORD:
            user_logged_in = True
            
            return redirect(url_for('scan_qr'))
    return render_template('user_login.html')

@app.route('/logout')
def logout():
    global admin_logged_in, user_logged_in
    admin_logged_in = False
    user_logged_in = False
    return redirect(url_for('index'))

@app.route('/save_data', methods=['POST'])
def save_data():
    try:
        data = request.json.get('data')

        if data:
            import re
            match = re.search(r'ID: (\d+)', data)
            if match:
                id_value = match.group(1)
                connection = mysql.connector.connect(**db_config)
                cursor = connection.cursor()
                cursor.execute("INSERT INTO attendance (Data, ID) VALUES (%s, %s)", (data, id_value))
                connection.commit()
                cursor.close()
                connection.close()

                return 'Data saved successfully', 200
            else:
                return 'No ID found in data', 400
        else:
            return 'No data to save', 400
    except Exception as e:
        return f'Error saving data: {str(e)}', 500
    
@app.route('/display_data', methods=['GET', 'POST'])
def display_data():
    if request.method == 'POST':
        try:
            search_id = request.form['id']
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()
            select_query = "SELECT Data, ID FROM attendance WHERE ID = %s"
            cursor.execute(select_query, (search_id,))
            data = cursor.fetchall()
            cursor.close()
            connection.close()
            return render_template('display_data.html', data=data, search_id=search_id)

        except Exception as e:
            return f'Error fetching data: {str(e)}', 500

    return render_template('user_input.html')

if __name__ == '__main__':
    app.run(debug=True)
