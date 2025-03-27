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

        # connect to localhost and db

        # insert the records into the doctors tables
        cursor = conn.cursor()
        try:
            sql = "UPDATE `patients`  SET `fname` = %s,  `lname` = %s,  `email` = %s, `phone` = %s, " \
                  "`next_of_kin_name`=%s, `next_of_kin_phone`=%s,`subcounty`= %s  where patient_id = %s "
            cursor.execute(sql,
                           (fname, lname, email, phone, next_of_kin_name, next_of_kin_phone, subcounty, patient_id))
            conn.commit()
            flash('Update Successful', 'success')
            return redirect(url_for('patients'))

        except:
            flash('Update Failed, Please Try Again.', 'danger')
            return redirect(url_for('patients'))
    else:
        flash('Click the edit icon to update patient record.', 'info')
        return redirect(url_for('patients'))


@app.route('/test/<patient_id>')
def test(patient_id):
    if 'key' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('login'))

    u_email = session['key']

    # Fetch doctor information
    try:
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (u_email,))
        doctor = cursor.fetchone()
        print(doctor[1])  # Debugging purposes

    except sqlite3.Error as e:
        flash('An error occurred while fetching doctor information.', 'danger')
        print("Error fetching doctor information:", e)
        return render_template('error.html')

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
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tests(patient_id, weight, height, heart_rate, temperature, systolic, diastolic) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (patient_id, weight, height, heart_rate, temperature, systolic, diastolic,))
            conn.commit()
            flash('Record Saved Successfully.', 'success')
            return redirect(url_for('patients'))
        except sqlite3.Error as e:
            flash(f'An Error Occurred During Recording. {e}', 'danger')
            print(e)
            conn.rollback()
            print("Error:", e)
            return redirect(url_for('patients'))
    else:
        return render_template('add_healthresults.html')


@app.route('/individual_analysis/<id>')
def individual_analysis(id):
    cursor = conn.cursor()
    if 'key' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('login'))

    u_email = session['key']

    # Fetch doctor information
    try:
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (u_email,))
        doctor = cursor.fetchone()
        print(doctor[1])  # Debugging purposes

    except sqlite3.Error as e:
        flash('An error occurred while fetching doctor information.', 'danger')
        print("Error fetching doctor information:", e)
        return render_template('error.html')
    if id == "":
        return redirect('/patients')
    else:
        cursor = conn.cursor()
        cursor.execute("Select * from patients where id = %s", (id,))
        row_details = cursor.fetchone()

        cursor.execute(
            "Select * from tests where patient_id = %s order by test_date ASC", (id,))
        rows = cursor.fetchall()

        if not rows:
            flash('No Records for this patient.', 'warning')
            return redirect(url_for('patients'))
        else:
            sns.set_style('dark')
            plt.figure(figsize=(10, 6))

            # Convert fetched data to DataFrame for analysis
            data = pd.DataFrame(rows, columns=['id', 'patient_id', 'weight', 'height',
                                'heart_rate', 'temperature', 'systolic', 'diastolic', 'created_date'])
            data['created_date'] = pd.to_datetime(data['created_date'])

            # Perform data analysis and generate plots
            patterns = data[['temperature', 'created_date']]
            patterns = patterns.set_index('created_date')
            patterns.resample('ME').mean().plot(
                title='ANALYSIS OF TEMPERATURE')
            plt.xlabel("Month")
            plt.ylabel("Temperature in Degrees")
            plt.savefig("static/temp.png")
            plt.close()

            # Add similar code for other analyses (weight, heart rate, etc.)

            return render_template('individual_analysis.html', rows=rows, row_details=row_details, doctor=doctor, patient_id=id)


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
    # Connect to database
    cursor = conn.cursor()
    if 'key' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('login'))

    u_email = session['key']

    # Fetch doctor information
    try:
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (u_email,))
        doctor = cursor.fetchone()
        print(doctor[1])  # Debugging purposes

    except sqlite3.Error as e:
        flash('An error occurred while fetching doctor information.', 'danger')
        print("Error fetching doctor information:", e)
        return render_template('error.html')

    sql1 = "select * from patients  where id =%s"
    cursor.execute(sql1, (patient_id))
    row = cursor.fetchone()
    phone = row[5]
    print(phone)

    # execute the query using the cursor
    sql = "select * from prescription  where patient_id = %s order by date_created desc"
    cursor.execute(sql, (patient_id))
    # check if no records were found
    if cursor.rowcount < 1:
        flash('No prescription for this patient', 'danger')
        return render_template('prescription.html', patient_id=patient_id, token=1)
    else:
        # return all rows found
        # Search
        import pandas
        data = pandas.read_sql("select * from prescription where patient_id = %(id)s", conn,
                               parse_dates=['date_created'],
                               params={"id": patient_id})
        print('here', data)
        import matplotlib.pyplot as plt
        if data.empty:
            print('DataFrame is empty!')

        plt.style.use('ggplot')

        x, y = plt.subplots()
        data.groupby("medicine").size().plot(
            kind='pie', title='PERCENTAGE OF MEDICINE GIVEN', autopct='%1.1f%%')
        plt.xlabel("")
        plt.ylabel("")
        plt.savefig("static/pie.png")

        from matplotlib import rcParams
        rcParams.update({'figure.autolayout': True})

        x, y = plt.subplots()
        data.groupby("medicine")['duration'].mean().plot(
            kind='bar', color='blue', title='MEDICINE BY DURATION')
        plt.xlabel("Medicine")
        plt.ylabel("Duration - Days")
        plt.savefig("static/bar_count.png")

        x, y = plt.subplots()
        plt.ylim(0, 10)
        data.groupby("medicine")['medicine'].count().plot(
            kind='bar', title='MEDICATION')
        plt.xlabel("Medicine Name")
        plt.ylabel("Number of times given")
        plt.savefig("static/bar.png")

        x, y = plt.subplots()
        data = pandas.read_sql("select * from prescription where patient_id = %(id)s ", conn,
                               parse_dates=['date_created'],
                               params={"id": patient_id})

        data['date_created'] = pandas.to_datetime(data['date_created']).dt.date

        data = data.groupby(["date_created", "medicine"]).size().unstack()

        data.plot(kind='bar', title='ANALYSIS OF MEDICATION GIVEN BY DATE')
        plt.xlabel("Date Prescribed")
        plt.ylabel("Medication Given")
        plt.legend(bbox_to_anchor=(1.1, 1.05))
        plt.savefig("static/bar_drugs.png")

        flash('This page automatically generates an analysis of your patients prescriptions:', 'info')
        rows = cursor.fetchall()
        print(patient_id)
        return render_template('prescription.html', rows=rows, patient_id=patient_id, phone=phone,doctor=doctor)


@app.route('/add_prescription', methods=['POST', 'GET'])
def add_prescription():
    if 'key' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('login'))

    u_email = session['key']

    # Fetch doctor information
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (u_email,))
        doctor = cursor.fetchone()
        print(doctor[1])  # Debugging purposes

    except sqlite3.Error as e:
        flash('An error occurred while fetching doctor information.', 'danger')
        print("Error fetching doctor information:", e)
        return render_template('error.html')

    if request.method == "POST":
        patient_id = request.form['patient_id']
        prescription_name = request.form['prescription_name']
        dosage = request.form['dosage']
        duration = request.form['duration']

        try:
            cursor.execute(
                "INSERT INTO prescription (patient_id, medicine, dosage, duration) VALUES (%s, %s, %s, %s)",
                (patient_id, prescription_name, dosage, duration))
            conn.commit()
            flash('Prescription Saved Successfully', 'success')
            return redirect(url_for('prescription', patient_id=patient_id))

        except sqlite3.Error as e:
            flash('Error Occurred During Recording', 'danger')
            print("Error inserting prescription:", e)
            return redirect(url_for('patients', patient_id=patient_id))

    else:
        # You need to specify the template to render here
        return render_template('error.html')


# get prescription by prescription_id
@app.route('/view_prescription_to_edit/<prescription_id>/<patient_id>')
def view_prescription_to_edit(prescription_id, patient_id):
    # fetch the details of the patient
    cursor = conn.cursor()
    sql = 'Select * from prescription where prescription_id = %s'
    cursor.execute(sql, (prescription_id))

    if cursor.rowcount == 0:
        flash('Please click on Records Button to get patients records', 'danger')
        return redirect(url_for('patients'))
    else:
        row = cursor.fetchone()
        return render_template('prescription_update.html', row=row, patient_id=patient_id)


@app.route('/update_prescription', methods=['POST', 'GET'])
def update_prescription():
    if request.method == "POST":
        patient_idd = request.form['patient_id']
        prescription_id = request.form['prescription_id']
        prescription_name = request.form['prescription_name']
        dosage = request.form['dosage']
        duration = request.form['duration']

        # insert the records into the table
        cursor = conn.cursor()
        try:
            sql = "UPDATE `prescription`  SET `medicine` = %s,  `dosage` = %s,  `duration` = %s  where " \
                  "prescription_id = %s "
            cursor.execute(sql,
                           (prescription_name, dosage, duration, prescription_id))
            conn.commit()
            flash('Prescription Updated Successfully.', 'success')
            return redirect(url_for('prescription', patient_id=patient_idd))

        except:
            flash('Update Failed, Please Try Again.', 'danger')
            return redirect(url_for('prescription', patient_id=patient_idd))
    else:
        flash('Please the edit icon to update patient record.', 'info')
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

        # connect to localhost and db

        # insert the records into table
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO `weeks`(`patient_id`, `weeks`) values (%s,%s)", (patient_id, weeks))
            conn.commit()
            flash('Record Saved Successfully.', 'success')
            return redirect(url_for('patients'))

        except:
            flash('Error Occurred During Recording.', 'danger')
            return redirect(url_for('patients'))

    else:
        return render_template('add_healthresults.html')


@app.route('/change_profile', methods=['POST', 'GET'])
def change_profile():
    if 'key' in session:
        email = session['key']

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

@app.route('/predict', methods=['POST', 'GET'])
def predict():
    cursor = conn.cursor()
    if 'key' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('login'))

    u_email = session['key']

    # Fetch doctor information
    try:
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (u_email,))
        doctor = cursor.fetchone()
        print(doctor[1])  # Debugging purposes
    except sqlite3.Error as e:
        flash('An error occurred while fetching doctor information.', 'danger')
        print("Error fetching doctor information:", e)
        return render_template('error.html')

    if request.method == "POST":
        weight = float(request.form['weight'])
        height = float(request.form['height'])
        heart_rate = float(request.form['heart_rate'])
        temperature = float(request.form['temperature'])
        age = int(request.form['age'])

        def from_dob_to_age(born):
            today = datetime.date.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

        from datetime import date
        import datetime

        from matplotlib import rcParams
        rcParams.update({'figure.autolayout': True})

        data = pandas.read_sql(
            "SELECT patients.id, patients.dob, tests.weight, tests.height, tests.heart_rate, "
            "tests.temperature, tests.systolic, tests.diastolic FROM patients INNER JOIN tests ON patients.id "
            "= tests.patient_id",
            conn, parse_dates=['dob']
        )
        print(data)
        data['dob'] = data['dob'].apply(lambda x: from_dob_to_age(x))

        data['systolic'] = data['systolic'].astype(float)
        data['diastolic'] = data['diastolic'].astype(float)
        data['weight'] = data['weight'].astype(float)
        data['height'] = data['height'].astype(float)
        data['heart_rate'] = data['heart_rate'].astype(float)
        data['temperature'] = data['temperature'].astype(float)

        def conditions(s):
            if (s['systolic'] >= 140) or (s['diastolic'] >= 90):
                return 'High probability of having HDP'
            else:
                return 'Less probability of having HDP'

        data['class'] = data.apply(conditions, axis=1)
        print(data)

        print(data.groupby('class').size())

        print(data.isnull().sum())
        print(data.dtypes)

        # Step 1: Split to X, Y
        array = data.values
        X = array[:, [1, 2, 3, 4, 5]]  # 5 features: age, weight, height, heart_rate, temperature
        Y = array[:, -1]  # class target

        # Step 2: Train the model
        from sklearn import model_selection
        X_train, X_test, Y_train, Y_test = model_selection.train_test_split(X, Y, test_size=0.30, random_state=42)

        # Cross validation of models to find out which could perform better
        models = [
            ('DTree', DecisionTreeClassifier()),
            ('Gaussian', GaussianNB()),
            ('KNN', KNeighborsClassifier()),
            ('LogisticReg', LogisticRegression(solver='liblinear', multi_class='ovr')),
            ('Gradient Boosting', GradientBoostingClassifier()),
            ('Linear Disc', LinearDiscriminantAnalysis())
        ]

        from sklearn.model_selection import cross_val_score, KFold

        for name, model in models:
            n_splits = min(10, len(X_train))  # Ensure n_splits does not exceed number of samples
            kfold = KFold(n_splits=n_splits, random_state=42, shuffle=True)
            cv_results = cross_val_score(model, X_train, Y_train, cv=kfold, scoring='accuracy')
            print('Model Name ', name, 'Results', cv_results.mean())

        # Pick GradientBoostingClassifier as it scored higher from the cross-validation
        model = GradientBoostingClassifier()
        model.fit(X_train, Y_train)

        # Ask the model to predict 30% test data
        predictions = model.predict(X_test)

        # Check accuracy
        from sklearn.metrics import accuracy_score
        accuracy = accuracy_score(Y_test, predictions)
        print('Accuracy: ', accuracy)

        from sklearn.metrics import classification_report
        from sklearn.metrics import confusion_matrix
        print('Report: ', classification_report(Y_test, predictions))
        print(confusion_matrix(Y_test, predictions))

        # Provide data from doctor input
        inputs = [[age, weight, height, heart_rate, temperature]]
        outcome = model.predict(inputs)[0]  # Predict the outcome
        print('Prediction ', outcome)

        flash('Prediction Successful', 'success')
        return render_template('predict.html', Likelihood='Likelihood: ' + outcome, accuracy_score='The accuracy: ' + str(round(accuracy, 2)))
    else:
        return render_template('predict.html', doctor=doctor)


@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response


if __name__ == '__main__':
    app.run(debug=True)
