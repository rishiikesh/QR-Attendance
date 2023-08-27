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

# Initialize variables to track user sessions
admin_logged_in = False
user_logged_in = True

# MySQL Database Configuration

db_config = {
    'user': 'root',
    'password': 'root',
    'database': 'info'
}

# Create a MySQL database connection
db_conn = mysql.connector.connect(**db_config)

# Create a cursor to execute SQL queries
db_cursor = db_conn.cursor()

# Define a table creation query
create_table_query = """
CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    rollno VARCHAR(10),
    student_id VARCHAR(10),
    scanned_data VARCHAR(80)
)
"""

# Execute the table creation query
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

        # Convert the QR code image to base64 string
        buffered = io.BytesIO()
        qr.save(buffered, format='PNG')
        qr_image_base64 = base64.b64encode(buffered.getvalue()).decode()
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
            
            # Extract student information from scanned data
            student_info = data.split('\n')
            
            if len(student_info) >= 3:
                name = student_info[0].split(': ')[1]
                rollno = student_info[1].split(': ')[1]
                student_id = student_info[2].split(': ')[1]
                scannedData = scannedData[3].split(': ')[1]
                
                # Insert scanned data into the 'students' table
                insert_query = "INSERT INTO students (name, rollno, student_id,scanned_data) VALUES (%s, %s, %s, %s)"
                insert_data = (name, rollno, student_id, scannedData)
                
                db_cursor.execute(insert_query, insert_data)
                db_conn.commit()
                
                return jsonify({'scannedData': data, 'saved': True})
            else:
                return jsonify({'scannedData': 'Invalid QR code data.'})
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
            return redirect(url_for('index'))
    return render_template('admin_login.html')

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    global user_logged_in
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USER_USERNAME and password == USER_PASSWORD:
            user_logged_in = True
            return redirect(url_for('generate_qr'))
    return render_template('user_login.html')

@app.route('/logout')
def logout():
    global admin_logged_in, user_logged_in
    admin_logged_in = False
    user_logged_in = False
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
