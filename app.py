from datetime import datetime, date
from matplotlib import rcParams
from flask import Flask, render_template
from flask import Flask, render_template, session, flash, redirect, url_for
from flask import request
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as snsimport
import numpy as np
# functions to hash password
import hashlib  # secure hashes and message digests
import binascii  # convert between binary and ASCII
import os  # provides functions for interacting with the os
import seaborn as sns
import logging
from sklearn.model_selection import train_test_split, StratifiedKFold, LeaveOneOut, cross_val_score
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from datetime import datetime
import warnings
from sklearn.exceptions import FitFailedWarning
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import pandas

# flask object takes the the name of the application, assign app to flask class,to identify current module being
# parsed to flask
app = Flask(__name__)

# create a secret key used in encrypting the sessions for security
app.secret_key = "Wdg@#$%89jMfh2879mT"

# SQLite database connection
def get_db_connection():
    conn = sqlite3.connect('sosmama.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        hospital_name TEXT,
        location TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create patients table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_number TEXT UNIQUE NOT NULL,
        fname TEXT NOT NULL,
        lname TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        next_of_kin_name TEXT,
        next_of_kin_phone TEXT,
        dob DATE,
        subcounty TEXT,
        county TEXT,
        date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create tests table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        weight REAL,
        height REAL,
        heart_rate INTEGER,
        temperature REAL,
        systolic INTEGER,
        diastolic INTEGER,
        test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients (id)
    )
    ''')
    
    # Create prescription table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS prescription (
        prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        medicine TEXT NOT NULL,
        dosage TEXT,
        duration TEXT,
        date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients (id)
    )
    ''')
    
    # Create weeks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS weeks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        weeks INTEGER,
        date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize the database when the app starts
init_db()

# This function receives a password as a parameter
# its hashes and salts using sha512 encoding
# hash_p encodes a provided password in a way that is safe to store on a database
def hash_password(password):
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                  salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


# this function checks if hashed password is the same as
# provided password
def verify_password(hashed_password, provided_password):
    # Verify a stored password against one provided by user
    salt = hashed_password[:64]
    hashed_password = hashed_password[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha512',
                                  provided_password.encode('utf-8'),
                                  salt.encode('ascii'),
                                  100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == hashed_password


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


# Login.html route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            conn.close()

            if user and verify_password(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Login successful!', 'success')
                return redirect(url_for('patients'))
            else:
                flash('Invalid username or password.', 'danger')
        except sqlite3.Error as e:
            flash('An error occurred during login.', 'danger')
            conn.close()

    return render_template('login.html')


# signup.html route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form['phone']
        hospital_name = request.form['hospital_name']
        location = request.form['location']
        confirm = request.form['confirm']

        # Validate password
        if password != confirm:
            flash('Password does not match!', 'danger')
            return render_template('signup.html')
        
        if len(password) < 8:
            flash('Password must be eight characters long!', 'danger')
            return render_template('signup.html')

        hashed_password = hash_password(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, password, email, phone, hospital_name, location)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, hashed_password, email, phone, hospital_name, location))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError as e:
            flash('Username or email already exists.', 'danger')
        finally:
            conn.close()

    return render_template('signup.html')


# patients.html route
@app.route('/patients', methods=['POST', 'GET'])
def patients():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Fetch doctor information
        cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
        doctor = cursor.fetchone()

        # Handle POST request for patient search
        if request.method == "POST":
            phone = request.form['phone']
            cursor.execute('SELECT * FROM patients WHERE phone = ?', (phone,))
            rows = cursor.fetchall()

            if not rows:
                flash('No patient found with the provided phone number.', 'info')
        else:
            # Handle GET request to fetch all patients
            cursor.execute('SELECT * FROM patients ORDER BY date_created DESC')
            rows = cursor.fetchall()

            if not rows:
                flash('No patients in records. Please add patients.', 'info')

        return render_template('patients.html', rows=rows, doctor=doctor)

    except sqlite3.Error as e:
        flash('An error occurred while accessing the database.', 'danger')
        print("Database error:", e)
        return render_template('error.html')
    finally:
        conn.close()


# Add patient button route
@app.route('/add', methods=['POST', 'GET'])
def add():
    if request.method == "POST":
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        phone = request.form['phone']
        id_number = request.form['id_number']
        next_of_kin_name = request.form['next_of_kin_name']
        next_of_kin_phone = request.form['next_of_kin_phone']
        subcounty = request.form['subcounty']
        dob = request.form['dob']
        county = request.form['county']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO patients (id_number, fname, lname, email, phone,
                next_of_kin_name, next_of_kin_phone, dob, subcounty, county)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (id_number, fname, lname, email, phone, next_of_kin_name, 
                 next_of_kin_phone, dob, subcounty, county))
            conn.commit()
            flash('Record Saved Successfully.', 'success')
            return redirect(url_for('patients'))
        except sqlite3.IntegrityError as e:
            flash('Sorry, an error occurred during Registration, ID number or telephone is already used.', 'danger')
            conn.rollback()
        finally:
            conn.close()

    return redirect(url_for('patients'))


# provide the patient id to update
# provide the patient id to retrieve the patient record
# patient_update.html route
@app.route('/retrieve_patient_to_update/<patient_id>', methods=['POST', 'GET'])
def retrieve_patient_to_update(patient_id):
    # fetch the details of the patient
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = 'Select * from patients where patient_id = %s'
    cursor.execute(sql, patient_id)

    if cursor.rowcount == 0:
        flash('No Records ', 'danger')
        return redirect(url_for('patients'))
    else:
        row = cursor.fetchone()
        # return the records to patient_update.html and place fields in the form for doctor to change
        return render_template('patient_update.html', row=row)


@app.route('/update_patient', methods=['POST', 'GET'])
def update_patient():
    if request.method == "POST":
        patient_id = request.form['patient_id']
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        phone = request.form['phone']
        next_of_kin_name = request.form['next_of_kin_name']
        next_of_kin_phone = request.form['next_of_kin_phone']
        subcounty = request.form['subcounty']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE patients 
                SET fname = ?, lname = ?, email = ?, phone = ?,
                    next_of_kin_name = ?, next_of_kin_phone = ?, subcounty = ?
                WHERE id = ?
            ''', (fname, lname, email, phone, next_of_kin_name, next_of_kin_phone, subcounty, patient_id))
            conn.commit()
            flash('Update Successful', 'success')
            return redirect(url_for('patients'))
        except sqlite3.Error as e:
            flash('Update Failed, Please Try Again.', 'danger')
            conn.rollback()
        finally:
            conn.close()
    else:
        flash('Click the edit icon to update patient record.', 'info')
        return redirect(url_for('patients'))


@app.route('/test/<patient_id>')
def test(patient_id):
    if 'key' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('login'))

    u_email = session['key']
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM users WHERE email = ?', (u_email,))
        doctor = cursor.fetchone()
    except sqlite3.Error as e:
        flash('An error occurred while fetching doctor information.', 'danger')
        print("Error fetching doctor information:", e)
        return render_template('error.html')
    finally:
        conn.close()

    return render_template('add_healthresults.html', patient_id=patient_id, doctor=doctor)


@app.route('/add_healthresults', methods=['POST', 'GET'])
def add_healthresults():
    if request.method == "POST":
        patient_id = request.form['id']
        weight = request.form['weight']
        height = request.form['height']
        heart_rate = request.form['heart_rate']
        temperature = request.form['temperature']
        systolic = request.form['systolic']
        diastolic = request.form['diastolic']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO tests (patient_id, weight, height, heart_rate, temperature, systolic, diastolic)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (patient_id, weight, height, heart_rate, temperature, systolic, diastolic))
            conn.commit()
            flash('Record Saved Successfully.', 'success')
            return redirect(url_for('patients'))
        except sqlite3.Error as e:
            flash(f'An Error Occurred During Recording. {e}', 'danger')
            conn.rollback()
        finally:
            conn.close()
    else:
        return render_template('add_healthresults.html')


@app.route('/individual_analysis/<id>')
def individual_analysis(id):
    if 'key' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('login'))

    u_email = session['key']
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM users WHERE email = ?', (u_email,))
        doctor = cursor.fetchone()
        
        if id == "":
            return redirect('/patients')
            
        cursor.execute('SELECT * FROM patients WHERE id = ?', (id,))
        row_details = cursor.fetchone()
        
        cursor.execute('SELECT * FROM tests WHERE patient_id = ? ORDER BY test_date ASC', (id,))
        rows = cursor.fetchall()

        if not rows:
            flash('No Records for this patient.', 'warning')
            return redirect(url_for('patients'))
            
        sns.set_style('dark')
        plt.figure(figsize=(10, 6))

        data = pd.DataFrame(rows, columns=['id', 'patient_id', 'weight', 'height',
                            'heart_rate', 'temperature', 'systolic', 'diastolic', 'created_date'])
        data['created_date'] = pd.to_datetime(data['created_date'])

        patterns = data[['temperature', 'created_date']]
        patterns = patterns.set_index('created_date')
        patterns.resample('ME').mean().plot(title='ANALYSIS OF TEMPERATURE')
        plt.xlabel("Month")
        plt.ylabel("Temperature in Degrees")
        plt.savefig("static/temp.png")
        plt.close()

        return render_template('individual_analysis.html', rows=rows, row_details=row_details, doctor=doctor, patient_id=id)
    except sqlite3.Error as e:
        flash('An error occurred while accessing the database.', 'danger')
        return render_template('error.html')
    finally:
        conn.close()


# @app.route('/prescription/')
# def prescription_list():
    # if 'key' not in session:
    #     flash('Please log in to access this page.', 'info')
    #     return redirect(url_for('login'))

    # u_email = session['key']

    # # Fetch doctor information
    # try:
    #     query = "SELECT * FROM users WHERE email = %s"
    #     cursor.execute(query, (u_email,))
    #     doctor = cursor.fetchone()
    #     print(doctor[1])  # Debugging purposes

    # except sqlite3.Error as e:
    #     flash('An error occurred while fetching doctor information.', 'danger')
    #     print("Error fetching doctor information:", e)
    #     return render_template('error.html')
#     cursor.execute("SELECT * FROM prescription")
#     prescriptions = cursor.fetchall()

#     # Close the cursor and connection
#     cursor.close()
#     conn.close()

#     # Render a template to display the prescription list
#     return render_template('prescription.html', prescriptions=prescriptions,doctor=doctor)

# view prescription by patient
@app.route('/prescription/<patient_id>')
def prescription(patient_id):
    if 'key' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('login'))

    u_email = session['key']
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM users WHERE email = ?', (u_email,))
        doctor = cursor.fetchone()

        cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
        row = cursor.fetchone()
        phone = row[5]

        cursor.execute('SELECT * FROM prescription WHERE patient_id = ? ORDER BY date_created DESC', (patient_id,))
        if cursor.rowcount < 1:
            flash('No prescription for this patient', 'danger')
            return render_template('prescription.html', patient_id=patient_id, token=1)

        data = pd.read_sql('SELECT * FROM prescription WHERE patient_id = ?', conn, params={"id": patient_id}, parse_dates=['date_created'])
        
        # Generate plots
        plt.style.use('ggplot')
        
        # Pie chart
        plt.figure()
        data.groupby("medicine").size().plot(kind='pie', title='PERCENTAGE OF MEDICINE GIVEN', autopct='%1.1f%%')
        plt.savefig("static/pie.png")
        plt.close()

        # Bar chart for duration
        plt.figure()
        data.groupby("medicine")['duration'].mean().plot(kind='bar', color='blue', title='MEDICINE BY DURATION')
        plt.xlabel("Medicine")
        plt.ylabel("Duration - Days")
        plt.savefig("static/bar_count.png")
        plt.close()

        # Bar chart for medication count
        plt.figure()
        plt.ylim(0, 10)
        data.groupby("medicine")['medicine'].count().plot(kind='bar', title='MEDICATION')
        plt.xlabel("Medicine Name")
        plt.ylabel("Number of times given")
        plt.savefig("static/bar.png")
        plt.close()

        # Bar chart for medication by date
        plt.figure()
        data['date_created'] = pd.to_datetime(data['date_created']).dt.date
        data.groupby(["date_created", "medicine"]).size().unstack().plot(kind='bar', title='ANALYSIS OF MEDICATION GIVEN BY DATE')
        plt.xlabel("Date Prescribed")
        plt.ylabel("Medication Given")
        plt.legend(bbox_to_anchor=(1.1, 1.05))
        plt.savefig("static/bar_drugs.png")
        plt.close()

        flash('This page automatically generates an analysis of your patients prescriptions:', 'info')
        return render_template('prescription.html', rows=data.to_dict('records'), patient_id=patient_id, phone=phone, doctor=doctor)

    except sqlite3.Error as e:
        flash('An error occurred while accessing the database.', 'danger')
        return render_template('error.html')
    finally:
        conn.close()


@app.route('/add_prescription', methods=['POST', 'GET'])
def add_prescription():
    if 'key' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('login'))

    u_email = session['key']
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM users WHERE email = ?', (u_email,))
        doctor = cursor.fetchone()

        if request.method == "POST":
            patient_id = request.form['patient_id']
            prescription_name = request.form['prescription_name']
            dosage = request.form['dosage']
            duration = request.form['duration']

            cursor.execute('''
                INSERT INTO prescription (patient_id, medicine, dosage, duration)
                VALUES (?, ?, ?, ?)
            ''', (patient_id, prescription_name, dosage, duration))
            conn.commit()
            flash('Prescription Saved Successfully', 'success')
            return redirect(url_for('prescription', patient_id=patient_id))

    except sqlite3.Error as e:
        flash('Error Occurred During Recording', 'danger')
        return redirect(url_for('patients'))
    finally:
        conn.close()

    return render_template('add_prescription.html', doctor=doctor)


# get prescription by prescription_id
@app.route('/view_prescription_to_edit/<prescription_id>/<patient_id>')
def view_prescription_to_edit(prescription_id, patient_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM prescription WHERE prescription_id = ?', (prescription_id,))
        if cursor.rowcount == 0:
            flash('Please click on Records Button to get patients records', 'danger')
            return redirect(url_for('patients'))
        
        row = cursor.fetchone()
        return render_template('prescription_update.html', row=row, patient_id=patient_id)
    except sqlite3.Error as e:
        flash('An error occurred while accessing the database.', 'danger')
        return render_template('error.html')
    finally:
        conn.close()


@app.route('/update_prescription', methods=['POST', 'GET'])
def update_prescription():
    if request.method == "POST":
        patient_idd = request.form['patient_id']
        prescription_id = request.form['prescription_id']
        prescription_name = request.form['prescription_name']
        dosage = request.form['dosage']
        duration = request.form['duration']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE prescription 
                SET medicine = ?, dosage = ?, duration = ?
                WHERE prescription_id = ?
            ''', (prescription_name, dosage, duration, prescription_id))
            conn.commit()
            flash('Prescription Updated Successfully.', 'success')
            return redirect(url_for('prescription', patient_id=patient_idd))
        except sqlite3.Error as e:
            flash('Update Failed, Please Try Again.', 'danger')
            conn.rollback()
        finally:
            conn.close()
    else:
        flash('Please click the edit icon to update patient record.', 'info')
        return redirect(url_for('patients'))


@app.route('/alert/<patient_phone>')
def alert(patient_phone):
    import africastalking
    africastalking.initialize

    sms = africastalking.SMS
    recipients = [patient_phone]
    message = 'You have a prescription from your doctor, please check your SOS MAMAS app on my prescriptions tab. ' \
              'Thank you. '

    try:
        response = sms.send(message, recipients)
        print(response)
    except Exception as e:
        print(f'Sorry, something went wrong: ${e}')

    print(f'Sorry, something went wrong: ${e}')

    return redirect('/patients')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/weeks', methods=['POST', 'GET'])
def weeks():
    if request.method == "POST":
        patient_id = request.form['patient_id']
        weeks = request.form['weeks']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO `weeks`(`patient_id`, `weeks`) values (?,?)", (patient_id, weeks))
            conn.commit()
            flash('Record Saved Successfully.', 'success')
            return redirect(url_for('patients'))

        except sqlite3.Error as e:
            flash('Error Occurred During Recording.', 'danger')
            return redirect(url_for('patients'))
        finally:
            conn.close()

    else:
        return render_template('add_healthresults.html')


@app.route('/change_profile', methods=['POST', 'GET'])
def change_profile():
    if 'key' in session:
        email = session['key']
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = 'Select * from users where email = %s'
        cursor.execute(sql, (email,))
        row = cursor.fetchone()
        return render_template('change_profile.html', row=row)
    else:
        return redirect('/login')


@app.route('/update_details', methods=['POST', 'GET'])
def update_details():
    if 'key' in session:
        email = session['key']
        if request.method == "POST":
            phone = request.form['phone']
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                sql = "UPDATE `users`  SET `phone` = %s  where " \
                      "email = %s "
                cursor.execute(sql,
                               (phone, email))
                conn.commit()
                flash('Contact Updated Successfully.', 'success')
                return redirect(url_for('patients'))

            except:
                flash('Update Failed, Please Try Again.', 'danger')
                return redirect(url_for('patients'))
        else:
            flash('Update Failed, Please Try Again.', 'info')
            return redirect(url_for('patients'))

    else:
        return redirect('/login')


@app.route('/view_profile')
def view_profile():
    if 'key' in session:
        email = session['key']
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = 'Select * from users where email = %s'
        cursor.execute(sql, (email,))
        row = cursor.fetchone()
        return render_template('profile.html', row=row)
    else:
        return redirect('/login')


def from_dob_to_age(dob):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def fetch_data(query, conn):
    return pd.read_sql(query, conn, parse_dates=['dob'])


def save_plot(x, y, xlabel, ylabel, title, filepath):
    y.set_xlabel(xlabel)
    y.set_ylabel(ylabel)
    y.set_title(title)
    x.savefig(filepath)

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Fetch doctor information
        cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
        doctor = cursor.fetchone()

        if request.method == 'POST':
            # Get form data
            patient_id = request.form.get('patient_id')
            weight = float(request.form.get('weight', 0))
            height = float(request.form.get('height', 0))
            heart_rate = int(request.form.get('heart_rate', 0))
            temperature = float(request.form.get('temperature', 0))
            systolic = int(request.form.get('systolic', 0))
            diastolic = int(request.form.get('diastolic', 0))
            weeks = int(request.form.get('weeks', 0))

            # Calculate BMI
            height_m = height / 100
            bmi = weight / (height_m * height_m)

            conn = get_db_connection()
            cursor = conn.cursor()
            # Store test data
            cursor.execute('''
                INSERT INTO tests (patient_id, weight, height, heart_rate, temperature, systolic, diastolic)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (patient_id, weight, height, heart_rate, temperature, systolic, diastolic))
            conn.commit()

            # Store weeks data
            cursor.execute('''
                INSERT INTO weeks (patient_id, weeks)
                VALUES (?, ?)
            ''', (patient_id, weeks))
            conn.commit()

            # Prepare data for prediction
            data = {
                'weight': weight,
                'height': height,
                'bmi': bmi,
                'heart_rate': heart_rate,
                'temperature': temperature,
                'systolic': systolic,
                'diastolic': diastolic,
                'weeks': weeks
            }

            # Make prediction using your model
            prediction = predict_preeclampsia(data)

            return render_template('prediction_result.html', 
                                 prediction=prediction, 
                                 data=data,
                                 doctor=doctor)

        # For GET request, show the prediction form
        cursor.execute('SELECT * FROM patients ORDER BY date_created DESC')
        patients = cursor.fetchall()
        return render_template('predict.html', patients=patients, doctor=doctor)

    except sqlite3.Error as e:
        flash('An error occurred while accessing the database.', 'danger')
        print("Database error:", e)
        return render_template('error.html')
    finally:
        conn.close()

def predict_preeclampsia(data):
    # Your prediction logic here
    # This is a placeholder - replace with your actual model
    risk_factors = 0
    
    # BMI check
    if data['bmi'] > 30:
        risk_factors += 1
    
    # Blood pressure check
    if data['systolic'] > 140 or data['diastolic'] > 90:
        risk_factors += 1
    
    # Heart rate check
    if data['heart_rate'] > 100:
        risk_factors += 1
    
    # Temperature check
    if data['temperature'] > 37.5:
        risk_factors += 1
    
    # Weeks check
    if data['weeks'] > 20:
        risk_factors += 1
    
    # Simple risk assessment
    if risk_factors >= 3:
        return "High Risk"
    elif risk_factors >= 1:
        return "Moderate Risk"
    else:
        return "Low Risk"

@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

