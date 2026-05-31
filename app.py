

from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_mysqldb import MySQL

import MySQLdb.cursors
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash   # <-- ADDED
import random, os
from datetime import datetime, timedelta
from flask_mail import Mail, Message
from functools import wraps

app = Flask(__name__)

app.secret_key = 'super_secret_key'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'lisamincigunnhildr@gmail.com'
app.config['MAIL_PASSWORD'] = "huaw qfnj inzi lvsj"
mail = Mail(app)

app.config['MYSQL_HOST'] = 'sql12.freesqldatabase.com'
app.config['MYSQL_USER'] = 'sql12828810'
app.config['MYSQL_PASSWORD'] = 'wZ5veTce9E'
app.config['MYSQL_DB'] = 'sql12828810'
mysql = MySQL(app)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session or session.get('usertype') != 'admin':
            flash("Admin access required.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap
@app.route("/dashboard")
@login_required
def user_dashboard():

    user_id = session["user_id"]

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1. Created events count
    cursor.execute("""
        SELECT COUNT(*) AS created
        FROM events
        WHERE created_by=%s
    """, (user_id,))
    created = cursor.fetchone()["created"]

    # 2. Joined events count
    cursor.execute("""
        SELECT COUNT(*) AS joined
        FROM event_participants
        WHERE user_id=%s
    """, (user_id,))
    joined = cursor.fetchone()["joined"]

    # 3. Total participants across YOUR events
    cursor.execute("""
        SELECT COUNT(*) AS total_participants
        FROM event_participants ep
        JOIN events e ON ep.event_id = e.event_id
        WHERE e.created_by=%s
    """, (user_id,))
    total_participants = cursor.fetchone()["total_participants"]

    # 4. My created events with participant count
    cursor.execute("""
        SELECT e.event_id, e.event_title,
               e.event_status,
               COUNT(ep.user_id) AS participants
        FROM events e
        LEFT JOIN event_participants ep
            ON e.event_id = ep.event_id
        WHERE e.created_by=%s
        GROUP BY e.event_id
        ORDER BY e.created_at DESC
    """, (user_id,))
    my_events = cursor.fetchall()

    # 5. Events user joined (details)
    cursor.execute("""
        SELECT e.*
        FROM events e
        JOIN event_participants ep
            ON e.event_id = ep.event_id
        WHERE ep.user_id=%s
        ORDER BY e.created_at DESC
    """, (user_id,))
    joined_events = cursor.fetchall()

    cursor.close()

    return render_template(
        "dashboard.html",
        created=created,
        joined=joined,
        total_participants=total_participants,
        my_events=my_events,
        joined_events=joined_events
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        phnum = request.form['phnum']
        password = request.form['password']
        street = request.form.get('street', '')
        province = request.form.get('province', '')
        region = request.form.get('region', '')
        birthdate = request.form.get('birthdate')
        usertype = 'user'
        profile_image = None

        hashed_password = generate_password_hash(password)   # <-- CHANGED

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM account_details WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("Email already exists!", "danger")
            return redirect(url_for('register'))

        cursor.execute("""
            INSERT INTO account_details (first_name, last_name, email, password_hash, contact_number,
             birthdate, profile_image, street, province, region, usertype)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (firstname, lastname, email, hashed_password, phnum, birthdate, profile_image,
              street, province, region, usertype))
        mysql.connection.commit()

        otp = str(random.randint(100000, 999999))
        expiry = datetime.now() + timedelta(minutes=5)
        cursor.execute("UPDATE account_details SET otp_code=%s, otp_expiry=%s WHERE email=%s",
                       (otp, expiry, email))
        mysql.connection.commit()

        msg = Message("Your OTP Code - EventNova", sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"Your OTP is {otp}. It expires in 5 minutes."
        mail.send(msg)

        return redirect(url_for('verify', email=email))
    return render_template('register.html')
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM account_details WHERE email=%s", (email,))
        account = cursor.fetchone()
        if account and check_password_hash(account['password_hash'], password):
            if not account['is_verified']:
                flash("Please verify your email first.", "warning")
                return redirect(url_for('verify', email=email))
            session['loggedin'] = True
            session['user_id'] = account['user_id']
            session['first_name'] = account['first_name']
            session['last_name'] = account['last_name']               # ✅ added
            session['contact_number'] = account['contact_number']     # ✅ added
            session['email'] = account['email']
            session['usertype'] = account['usertype']
            flash("Login successful!", "success")
            return redirect('/admin/dashboard' if account['usertype'] == 'admin' else '/dashboard')
        else:
            flash("Invalid email or password.", "danger")
    return render_template('login.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    email = request.args.get('email')
    if not email:
        return redirect(url_for('login'))
    if request.method == 'POST':
        otp = request.form['otp']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM account_details WHERE email=%s AND otp_code=%s", (email, otp))
        account = cursor.fetchone()
        if account:
            if datetime.now() > account['otp_expiry']:
                flash("OTP expired!", "danger")
                return redirect(url_for('verify', email=email))
            cursor.execute("UPDATE account_details SET is_verified=1, otp_code=NULL, otp_expiry=NULL WHERE email=%s", (email,))
            mysql.connection.commit()
            flash("Account verified successfully!", "success")
            return redirect(url_for('login'))
        else:
            flash("Invalid OTP.", "danger")
    return render_template('verify.html', email=email)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('user_id', None)
    session.pop('first_name', None)
    session.pop('email', None)
    session.pop('usertype', None)
    flash("Successfully logged out!", "success")
    return redirect(url_for('login'))

# ---------- User Pages ----------
@app.route('/dashboard')
@login_required
def dashboard():

    return render_template('dashboard.html')

@app.route("/browse-events")
@login_required
def browse_events():

    province = request.args.get("province", "")
    category = request.args.get("category", "")

    query = """
        SELECT
            e.*,
            a.first_name,
            a.last_name
        FROM events e
        JOIN account_details a
            ON e.created_by = a.user_id
        WHERE e.event_status='live'
    """

    params = []

    if province:
        query += " AND e.province LIKE %s"
        params.append(f"%{province}%")

    if category:
        query += " AND e.event_category LIKE %s"
        params.append(f"%{category}%")

    query += " ORDER BY e.event_start ASC"

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query, params)

    events = cursor.fetchall()

    cursor.close()

    return render_template(
        "browse_events.html",
        events=events
    )
@app.route("/event/<int:event_id>")
@login_required
def event_details(event_id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # -----------------------
    # EVENT INFO
    # -----------------------
    cursor.execute("""
        SELECT e.*, a.first_name, a.last_name
        FROM events e
        JOIN account_details a ON e.created_by = a.user_id
        WHERE e.event_id = %s
    """, (event_id,))

    event = cursor.fetchone()

    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("browse_events"))

    # -----------------------
    # PARTICIPANTS LIST
    # -----------------------
    cursor.execute("""
        SELECT a.first_name, a.last_name, a.email
        FROM event_participants ep
        JOIN account_details a ON ep.user_id = a.user_id
        WHERE ep.event_id = %s
    """, (event_id,))

    participants = cursor.fetchall()

    cursor.close()

    return render_template(
        "event_details.html",
        event=event,
        participants=participants
    )
@app.route("/join-event/<int:event_id>", methods=["POST"])
@login_required
def join_event(event_id):

    user_id = session["user_id"]

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO event_participants
            (
                event_id,
                user_id
            )
            VALUES
            (%s,%s)
        """, (
            event_id,
            user_id
        ))

        cursor.execute("""
            UPDATE events
            SET current_participants =
                current_participants + 1
            WHERE event_id=%s
        """, (event_id,))

        mysql.connection.commit()

        flash(
            "Successfully joined event!",
            "success"
        )

    except:

        flash(
            "You already joined this event.",
            "warning"
        )

    cursor.close()

    return redirect(
        url_for(
            "event_details",   event_id=event_id
        )
    )
    
@app.route("/event/<int:event_id>/edit")
@login_required
def edit_user_event(event_id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT *
        FROM events
        WHERE event_id=%s
    """, (event_id,))

    event = cursor.fetchone()
    cursor.close()

    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("joined_events"))

    if event["created_by"] != session["user_id"]:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("joined_events"))

    return render_template(
        "edit_user_event.html",
        event=event
    )
    
    
@app.route("/event/<int:event_id>/update", methods=["POST"])
@login_required
def update_user_event(event_id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT *
        FROM events
        WHERE event_id=%s
    """, (event_id,))

    event = cursor.fetchone()

    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("joined_events"))

    if event["created_by"] != session["user_id"]:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("joined_events"))

    # FORM DATA
    title = request.form["title"]
    description = request.form["description"]
    category = request.form["category"]
    event_type = request.form["event_type"]
    region = request.form["region"]
    province = request.form["province"]
    street = request.form["street"]
    event_start = request.form["event_start"]
    event_end = request.form["event_end"]
    max_participants = request.form["max_participants"]
    status = request.form["status"]

    # IMAGE UPLOAD
    image_file = request.files.get("event_image")
    filename = event["event_image"]

    if image_file and image_file.filename != "":
        filename = secure_filename(image_file.filename)

        upload_path = os.path.join("static/uploads")
        os.makedirs(upload_path, exist_ok=True)

        image_file.save(os.path.join(upload_path, filename))

    # UPDATE QUERY
    cursor.execute("""
        UPDATE events SET
            event_title=%s,
            event_description=%s,
            event_category=%s,
            event_type=%s,
            region=%s,
            province=%s,
            street=%s,
            event_start=%s,
            event_end=%s,
            max_participants=%s,
            event_status=%s,
            event_image=%s,
            updated_at=NOW()
        WHERE event_id=%s
    """, (
        title,
        description,
        category,
        event_type,
        region,
        province,
        street,
        event_start,
        event_end,
        max_participants,
        status,
        filename,
        event_id
    ))

    mysql.connection.commit()
    cursor.close()

    flash("Event updated successfully!", "success")

    return redirect(url_for("event_details", event_id=event_id))
@app.route("/event/<int:event_id>/delete")
@login_required
def delete_user_event(event_id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT created_by
        FROM events
        WHERE event_id=%s
    """, (event_id,))

    event = cursor.fetchone()

    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("my_events"))

    if event["created_by"] != session["user_id"]:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("my_events"))

    cursor.execute("""
        DELETE FROM events
        WHERE event_id=%s
    """, (event_id,))

    mysql.connection.commit()
    cursor.close()

    flash("Event deleted successfully!", "success")

    return redirect(url_for("my_events"))


@app.route("/my-events")
@login_required
def my_events():

    user_id = session["user_id"]

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # CREATED EVENTS
    cursor.execute("""
        SELECT *
        FROM events
        WHERE created_by = %s
        ORDER BY created_at DESC
    """, (user_id,))
    
    created_events = cursor.fetchall()

    # JOINED EVENTS
    cursor.execute("""
        SELECT
            e.*,
            ep.joined_at
        FROM event_participants ep
        JOIN events e
            ON ep.event_id = e.event_id
        WHERE ep.user_id = %s
        ORDER BY ep.joined_at DESC
    """, (user_id,))
    
    joined_events = cursor.fetchall()

    cursor.close()

    return render_template(
        "my_events.html",
        created_events=created_events,
        joined_events=joined_events
    )
    
@app.route("/leave-event/<int:event_id>")
@login_required
def leave_event(event_id):

    user_id = session["user_id"]

    cursor = mysql.connection.cursor()

    cursor.execute("""
        DELETE FROM event_participants
        WHERE event_id=%s
        AND user_id=%s
    """, (event_id, user_id))

    cursor.execute("""
        UPDATE events
        SET current_participants =
            GREATEST(current_participants - 1, 0)
        WHERE event_id=%s
    """, (event_id,))

    mysql.connection.commit()
    cursor.close()

    flash("You left the event.", "warning")

    return redirect(url_for("my_events"))
    

@app.route("/create_events", methods=["GET", "POST"])
def create_events():

   
    if request.method == "GET":
        
        return render_template(

    "create_events.html",

    first_name=session.get("first_name"),

    last_name=session.get("last_name"),

    email=session.get("email"),

    phone=session.get("contact_number") 

)


    # =========================
    # POST: SAVE EVENT
    # =========================
    try:

        title = request.form["title"]
        description = request.form["description"]
        category = request.form["category"]
        event_type = request.form["event_type"]

        region = request.form["region"]
        province = request.form["province"]
        street = request.form["street"]

        event_start = request.form["event_start"]
        event_end = request.form["event_end"]

        max_participants = request.form["max_participants"]
        status = request.form["status"]

        created_by = session["user_id"]

        # =========================
        # IMAGE UPLOAD
        # =========================
        image_file = request.files.get("event_image")
        filename = None

        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)

            upload_path = os.path.join("static/uploads")
            os.makedirs(upload_path, exist_ok=True)

            image_file.save(os.path.join(upload_path, filename))

        # =========================
        # INSERT DB
        # =========================
        cursor = mysql.connection.cursor()

        sql = """
            INSERT INTO events (
                event_title,
                event_description,
                event_category,
                event_type,
                region,
                province,
                street,
                event_start,
                event_end,
                max_participants,
                current_participants,
                event_image,
                event_status,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            title,
            description,
            category,
            event_type,
            region,
            province,
            street,
            event_start,
            event_end,
            max_participants,
            0,
            filename,
            status,
            created_by
        )

        cursor.execute(sql, values)
        mysql.connection.commit()
        cursor.close()

        # =========================
        # FLASH MESSAGE
        # =========================
        if status == "live":
            flash("Event published successfully!", "success")
        else:
            flash("Event saved as draft!", "secondary")

        return redirect("/create_events")

    except Exception as e:
        print("ERROR:", e)
        flash("Something went wrong while creating the event.", "danger")
        return redirect("/create_events")
@app.route('/joined-events')
@login_required
def joined_events():
   
    return render_template('joined_events.html')

@app.route('/userreport')
@login_required
def user_report():
  
    return render_template('userreport.html')
@app.route('/notifs')
@login_required
def notifications():
  
    return render_template('notifs.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        contact_number = request.form['contact_number']
        street = request.form['street']
        province = request.form['province']
        region = request.form['region']

        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Update profile info
        cursor.execute("""
            UPDATE account_details
            SET
                first_name=%s,
                last_name=%s,
                email=%s,
                contact_number=%s,
                street=%s,
                province=%s,
                region=%s
            WHERE user_id=%s
        """, (
            first_name,
            last_name,
            email,
            contact_number,
            street,
            province,
            region,
            user_id
        ))

        if password:
            if password != confirm_password:
                flash("Passwords do not match.", "danger")
                return redirect(url_for('profile'))
            
            hashed_password = generate_password_hash(password)   # <-- now works

            cursor.execute("""
                UPDATE account_details
                SET password_hash=%s
                WHERE user_id=%s
            """, (
                hashed_password,
                user_id
            ))

        mysql.connection.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    cursor.execute(
        "SELECT * FROM account_details WHERE user_id=%s",
        (user_id,)
    )
    user = cursor.fetchone()
    cursor.close()
    return render_template('profile.html', user=user)

# ---------- Admin Pages ----------
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # -------------------------
    # KPI COUNTS
    # -------------------------
    cursor.execute("SELECT COUNT(*) AS total_users FROM account_details")
    total_users = cursor.fetchone()["total_users"]

    cursor.execute("SELECT COUNT(*) AS total_events FROM events")
    total_events = cursor.fetchone()["total_events"]

    cursor.execute("""
        SELECT 
            SUM(CASE WHEN event_status='live' THEN 1 ELSE 0 END) AS live,
            SUM(CASE WHEN event_status='draft' THEN 1 ELSE 0 END) AS draft
        FROM events
    """)
    status = cursor.fetchone()

    live = status["live"] or 0
    draft = status["draft"] or 0

    # -------------------------
    # RECENT EVENTS
    # -------------------------
    cursor.execute("""
        SELECT 
            e.event_title,
            e.event_status,
            a.first_name,
            a.last_name
        FROM events e
        JOIN account_details a ON e.created_by = a.user_id
        ORDER BY e.created_at DESC
        LIMIT 5
    """)

    recent_events = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_events=total_events,
        live=live,
        draft=draft,
        recent_events=recent_events
    )



@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def manage_users():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':

        action = request.form.get('action')
        user_id = request.form.get('user_id')

        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        contact_number = request.form.get('contact_number')
        street = request.form.get('street')
        region = request.form.get('region')
        province = request.form.get('province')
        usertype = request.form.get('usertype')

        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # ==========================
        # ADD USER
        # ==========================
        if action == 'add':

            cursor.execute(
                "SELECT * FROM account_details WHERE email=%s",
                (email,)
            )

            if cursor.fetchone():
                flash("Email already exists.", "danger")
                return redirect(url_for('manage_users'))

            if password != confirm_password:
                flash("Passwords do not match.", "danger")
                return redirect(url_for('manage_users'))

            if not password:
                flash("Password is required.", "danger")
                return redirect(url_for('manage_users'))

            # --- CHANGED: use generate_password_hash ---
            hashed_password = generate_password_hash(password)

            cursor.execute("""
                INSERT INTO account_details
                (
                    first_name,
                    last_name,
                    email,
                    password_hash,
                    contact_number,
                    street,
                    region,
                    province,
                    usertype,
                    is_verified
                )
                VALUES
                (%s,%s,%s,%s,%s,%s,%s,%s,%s,1)
            """, (
                first_name,
                last_name,
                email,
                hashed_password,
                contact_number,
                street,
                region,
                province,
                usertype
            ))

            mysql.connection.commit()
            flash("User added successfully.", "success")

        # ==========================
        # EDIT USER
        # ==========================
        elif action == 'edit':

            cursor.execute("""
                UPDATE account_details
                SET
                    first_name=%s,
                    last_name=%s,
                    email=%s,
                    contact_number=%s,
                    street=%s,
                    region=%s,
                    province=%s,
                    usertype=%s
                WHERE user_id=%s
            """, (
                first_name,
                last_name,
                email,
                contact_number,
                street,
                region,
                province,
                usertype,
                user_id
            ))

            if password:

                if password != confirm_password:
                    flash("Passwords do not match.", "danger")
                    return redirect(url_for('manage_users'))

                # --- CHANGED: use generate_password_hash ---
                hashed_password = generate_password_hash(password)

                cursor.execute("""
                    UPDATE account_details
                    SET password_hash=%s
                    WHERE user_id=%s
                """, (
                    hashed_password,
                    user_id
                ))

            mysql.connection.commit()
            flash("User updated successfully.", "success")

        # ==========================
        # DELETE USER
        # ==========================
        elif action == 'delete':

            if not user_id:
                flash("Please select a user.", "danger")
                return redirect(url_for('manage_users'))

            # Prevent deleting yourself
            if int(user_id) == session['user_id']:
                flash("You cannot delete your own account.", "danger")
                return redirect(url_for('manage_users'))

            cursor.execute(
                "DELETE FROM account_details WHERE user_id=%s",
                (user_id,)
            )
            mysql.connection.commit()
            flash("User deleted successfully.", "success")

        return redirect(url_for('manage_users'))

    # ==========================
    # LOAD TABLE
    # ==========================
    cursor.execute("""
        SELECT *
        FROM account_details
        ORDER BY user_id DESC
    """)
    users = cursor.fetchall()
    cursor.close()

    return render_template('manage_users.html', users=users)


@app.route("/manage-events")
@admin_required
def manage_events():

    status = request.args.get("status")
    province = request.args.get("province")
    category = request.args.get("category")

    query = """
        SELECT 
            e.event_id,
            e.event_title,
            e.event_category,
            e.event_type,
            e.region,
            e.province,
            e.event_start,
            e.event_end,
            e.event_status,
            a.first_name,
            a.last_name,
            a.email,
            a.contact_number
        FROM events e
        JOIN account_details a ON e.created_by = a.user_id
        WHERE 1=1
    """

    params = []

    if status:
        query += " AND e.event_status=%s"
        params.append(status)

    if province:
        query += " AND e.province=%s"
        params.append(province)

    if category:
        query += " AND e.event_category=%s"
        params.append(category)

    query += " ORDER BY e.created_at DESC"

    cursor = mysql.connection.cursor()
    cursor.execute(query, params)
    events = cursor.fetchall()
    cursor.close()

    return render_template("manage_events.html", events=events)

@app.route("/manage-events/<int:event_id>/edit")
@admin_required
def edit_event(event_id):

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM events WHERE event_id=%s", (event_id,))
    event = cursor.fetchone()
    cursor.close()

    return render_template("edit_event.html", event=event)
@app.route("/manage-events/<int:event_id>/update", methods=["POST"])
@admin_required
def update_event(event_id):

    title = request.form["title"]
    description = request.form["description"]
    category = request.form["category"]
    event_type = request.form["event_type"]
    region = request.form["region"]
    province = request.form["province"]
    street = request.form["street"]
    event_start = request.form["event_start"]
    event_end = request.form["event_end"]
    max_participants = request.form["max_participants"]
    status = request.form["status"]

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE events SET
            event_title=%s,
            event_description=%s,
            event_category=%s,
            event_type=%s,
            region=%s,
            province=%s,
            street=%s,
            event_start=%s,
            event_end=%s,
            max_participants=%s,
            event_status=%s
        WHERE event_id=%s
    """, (
        title, description, category, event_type,
        region, province, street,
        event_start, event_end,
        max_participants, status,
        event_id
    ))

    mysql.connection.commit()
    cursor.close()

    flash("Event updated successfully!", "success")
    return redirect(url_for("manage_events"))

@app.route("/manage-events/<int:event_id>/delete")
@admin_required
def delete_event(event_id):

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM events WHERE event_id=%s", (event_id,))
    mysql.connection.commit()
    cursor.close()

    flash("Event deleted successfully!", "danger")
    return redirect(url_for("manage_events"))




@app.route('/admin/profile', methods=['GET', 'POST'])
@admin_required
def admin_profile():
    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        contact_number = request.form.get('contact_number')
        street = request.form.get('street')
        province = request.form.get('province')
        region = request.form.get('region')

        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        cursor.execute("""
            UPDATE account_details
            SET first_name=%s,
                last_name=%s,
                email=%s,
                contact_number=%s,
                street=%s,
                province=%s,
                region=%s
            WHERE user_id=%s
        """, (
            first_name,
            last_name,
            email,
            contact_number,
            street,
            province,
            region,
            user_id
        ))

        if password or confirm_password:
            if password != confirm_password:
                flash("Passwords do not match.", "danger")
                return redirect(url_for('admin_profile'))
            if len(password) < 6:
                flash("Password must be at least 6 characters.", "danger")
                return redirect(url_for('admin_profile'))
            hashed_password = generate_password_hash(password)   # <-- now works
            cursor.execute("""
                UPDATE account_details
                SET password_hash=%s
                WHERE user_id=%s
            """, (hashed_password, user_id))

        mysql.connection.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('admin_profile'))

    cursor.execute("SELECT * FROM account_details WHERE user_id=%s", (user_id,))
    admin = cursor.fetchone()
    cursor.close()
    return render_template('adminprofile.html', admin=admin)

@app.route('/admin/reports')
@admin_required
def manage_reports():
   
    return render_template('reports.html',)


@app.route('/admin/notifications', methods=['GET', 'POST'])
@admin_required
def admin_notifications():
   
    return render_template('adminnotifs.html')

@app.route('/admin/analytics')
@admin_required
def analytics():
  
    return render_template('analytics.html')


if __name__ == '__main__':
    app.run(debug=True)