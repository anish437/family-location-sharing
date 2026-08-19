from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for
)

import sqlite3
from datetime import datetime
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# =========================================================
# FLASK CONFIGURATION
# =========================================================

import os

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key"
)

DATABASE = "location.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection
# =========================================================
# CHECK FAMILY ADMIN
# =========================================================

def is_family_admin(user_id, family_id):

    if not user_id or not family_id:
        return False

    connection = get_db()

    admin = connection.execute(
        """
        SELECT id
        FROM families
        WHERE id = ?
        AND admin_user_id = ?
        """,
        (
            family_id,
            user_id
        )
    ).fetchone()

    connection.close()

    return admin is not None


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def create_database():

    connection = get_db()

    # =====================================================
    # USERS
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            username TEXT UNIQUE NOT NULL,

            password_hash TEXT NOT NULL,

            created_at TEXT

        )
    """)

    # =====================================================
    # FAMILIES
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS families (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            family_name TEXT NOT NULL,

            family_username TEXT UNIQUE NOT NULL,

            family_password_hash TEXT NOT NULL,

            admin_user_id INTEGER NOT NULL,

            created_at TEXT

        )
    """)

    # =====================================================
    # FAMILY MEMBERS
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS family_members (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            family_id INTEGER NOT NULL,

            user_id INTEGER NOT NULL,

            role TEXT NOT NULL DEFAULT 'member',

            status TEXT NOT NULL DEFAULT 'pending',

            is_sharing INTEGER NOT NULL DEFAULT 0,

            created_at TEXT,

            UNIQUE(family_id, user_id)

        )
    """)

    # =====================================================
    # LOCATIONS
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS locations (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            latitude REAL NOT NULL,

            longitude REAL NOT NULL,

            timestamp TEXT

        )
    """)

    connection.commit()


    # =====================================================
    # DATABASE MIGRATION
    # =====================================================

    cursor = connection.cursor()


    # -----------------------------------------------------
    # LOCATIONS -> user_id
    # -----------------------------------------------------

    cursor.execute("""
        PRAGMA table_info(locations)
    """)

    location_columns = [
        column[1]
        for column in cursor.fetchall()
    ]

    if "user_id" not in location_columns:

        connection.execute("""
            ALTER TABLE locations
            ADD COLUMN user_id INTEGER
        """)


    # -----------------------------------------------------
    # USERS -> created_at
    # -----------------------------------------------------

    cursor.execute("""
        PRAGMA table_info(users)
    """)

    user_columns = [
        column[1]
        for column in cursor.fetchall()
    ]

    if "created_at" not in user_columns:

        connection.execute("""
            ALTER TABLE users
            ADD COLUMN created_at TEXT
        """)


    # -----------------------------------------------------
    # FAMILIES -> created_at
    # -----------------------------------------------------

    cursor.execute("""
        PRAGMA table_info(families)
    """)

    family_columns = [
        column[1]
        for column in cursor.fetchall()
    ]

    if "created_at" not in family_columns:

        connection.execute("""
            ALTER TABLE families
            ADD COLUMN created_at TEXT
        """)


    # -----------------------------------------------------
    # FAMILY MEMBERS -> is_sharing
    # -----------------------------------------------------

    cursor.execute("""
        PRAGMA table_info(family_members)
    """)

    family_member_columns = [
        column[1]
        for column in cursor.fetchall()
    ]

    if "is_sharing" not in family_member_columns:

        connection.execute("""
            ALTER TABLE family_members
            ADD COLUMN is_sharing
            INTEGER NOT NULL DEFAULT 0
        """)


    # -----------------------------------------------------
    # FAMILY MEMBERS -> created_at
    # -----------------------------------------------------

    if "created_at" not in family_member_columns:

        connection.execute("""
            ALTER TABLE family_members
            ADD COLUMN created_at TEXT
        """)


    connection.commit()

    connection.close()


# =========================================================
# HOME
# =========================================================

# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "home.html"
    )

# =========================================================
# CREATE FAMILY
# =========================================================

@app.route(
    "/create-family",
    methods=["GET", "POST"]
)
def create_family():

    if request.method == "POST":

        # -------------------------------------------------
        # PERSONAL ACCOUNT
        # -------------------------------------------------

        name = request.form.get(
            "name",
            ""
        ).strip()

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        # -------------------------------------------------
        # FAMILY ACCOUNT
        # -------------------------------------------------

        family_name = request.form.get(
            "family_name",
            ""
        ).strip()

        family_username = request.form.get(
            "family_username",
            ""
        ).strip()

        family_password = request.form.get(
            "family_password",
            ""
        )


        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not name or not username or not password:

            return render_template(
                "create_family.html",
                error=(
                    "Please fill in all "
                    "personal account fields."
                )
            )


        if (
            not family_name
            or not family_username
            or not family_password
        ):

            return render_template(
                "create_family.html",
                error=(
                    "Please fill in all "
                    "family fields."
                )
            )


        connection = get_db()


        try:

            # ---------------------------------------------
            # CHECK PERSONAL USERNAME
            # ---------------------------------------------

            existing_user = connection.execute(
                """
                SELECT id
                FROM users
                WHERE username = ?
                """,
                (username,)
            ).fetchone()


            if existing_user:

                connection.close()

                return render_template(
                    "create_family.html",
                    error=(
                        "Personal username "
                        "already exists."
                    )
                )


            # ---------------------------------------------
            # CHECK FAMILY USERNAME
            # ---------------------------------------------

            existing_family = connection.execute(
                """
                SELECT id
                FROM families
                WHERE family_username = ?
                """,
                (family_username,)
            ).fetchone()


            if existing_family:

                connection.close()

                return render_template(
                    "create_family.html",
                    error=(
                        "Family username "
                        "already exists."
                    )
                )


            # ---------------------------------------------
            # CREATE USER
            # ---------------------------------------------

            cursor = connection.execute(
                """
                INSERT INTO users
                (
                    name,
                    username,
                    password_hash,
                    created_at
                )

                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    username,
                    generate_password_hash(
                        password
                    ),
                    datetime.now()
                )
            )


            user_id = cursor.lastrowid


            # ---------------------------------------------
            # CREATE FAMILY
            # ---------------------------------------------

            cursor = connection.execute(
                """
                INSERT INTO families
                (
                    family_name,
                    family_username,
                    family_password_hash,
                    admin_user_id,
                    created_at
                )

                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    family_name,
                    family_username,
                    generate_password_hash(
                        family_password
                    ),
                    user_id,
                    datetime.now()
                )
            )


            family_id = cursor.lastrowid


            # ---------------------------------------------
            # ADD CREATOR AS ADMIN
            # ---------------------------------------------

            connection.execute(
                """
                INSERT INTO family_members
                (
                    family_id,
                    user_id,
                    role,
                    status,
                    is_sharing,
                    created_at
                )

                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    family_id,
                    user_id,
                    "admin",
                    "approved",
                    0,
                    datetime.now()
                )
            )


            connection.commit()


        except sqlite3.IntegrityError as error:

            connection.rollback()

            connection.close()

            print(
                "Create family database error:",
                error
            )

            return render_template(
                "create_family.html",
                error=(
                    "Could not create "
                    "the family."
                )
            )


        connection.close()


        # ---------------------------------------------
        # LOGIN FAMILY ADMIN
        # ---------------------------------------------

        session.clear()

        session["user_id"] = user_id

        session["user_name"] = name

        session["family_id"] = family_id

        session["user_type"] = "family_admin"


        return redirect(
            url_for("family_dashboard")
        )


    return render_template(
        "create_family.html"
    )


# =========================================================
# FAMILY ADMIN DASHBOARD
# =========================================================

@app.route("/family-dashboard")
def family_dashboard():

    if session.get("user_type") != "family_admin":

        return redirect(
            url_for("create_family")
        )


    family_id = session.get(
        "family_id"
    )


    if not family_id:

        return redirect(
            url_for("create_family")
        )


    connection = get_db()
    


    # =====================================================
    # FAMILY INFORMATION
    # =====================================================

    family = connection.execute(
        """
        SELECT
            family_name,
            family_username
        FROM families
        WHERE id = ?
        """,
        (family_id,)
    ).fetchone()


    if not family:

        connection.close()

        session.clear()

        return redirect(
            url_for("create_family")
        )


    # =====================================================
    # APPROVED MEMBERS
    # =====================================================

    members = connection.execute(
        """
        SELECT
            family_members.id AS membership_id,

            users.id AS user_id,

            users.name,

            users.username,

            family_members.role,

            family_members.status,

            family_members.is_sharing

        FROM family_members

        JOIN users
            ON users.id =
               family_members.user_id

        WHERE family_members.family_id = ?

        AND family_members.status =
            'approved'

        ORDER BY users.name
        """,
        (family_id,)
    ).fetchall()


    # =====================================================
    # PENDING REQUESTS
    # =====================================================

    pending_requests = connection.execute(
        """
        SELECT
            family_members.id,
            users.name,
            users.username,
            family_members.created_at

        FROM family_members

        JOIN users
            ON users.id =
               family_members.user_id

        WHERE family_members.family_id = ?

        AND family_members.status =
            'pending'

        ORDER BY family_members.created_at
        """,
        (family_id,)
    ).fetchall()


    connection.close()


    return render_template(
        "family_dashboard.html",
        family=family,
        members=members,
        pending_requests=pending_requests
    )


# =========================================================
# JOIN FAMILY
# =========================================================

@app.route(
    "/join-family",
    methods=["GET", "POST"]
)
def join_family():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        family_username = request.form.get(
            "family_username",
            ""
        ).strip()

        family_password = request.form.get(
            "family_password",
            ""
        )


        if (
            not name
            or not username
            or not password
            or not family_username
            or not family_password
        ):

            return render_template(
                "join_family.html",
                error="Please fill in all fields."
            )


        connection = get_db()


        # =================================================
        # FIND FAMILY
        # =================================================

        family = connection.execute(
            """
            SELECT
                id,
                family_name,
                family_password_hash

            FROM families

            WHERE family_username = ?
            """,
            (family_username,)
        ).fetchone()


        if not family:

            connection.close()

            return render_template(
                "join_family.html",
                error=(
                    "Family username "
                    "was not found."
                )
            )


        # =================================================
        # CHECK FAMILY PASSWORD
        # =================================================

        if not check_password_hash(
            family["family_password_hash"],
            family_password
        ):

            connection.close()

            return render_template(
                "join_family.html",
                error=(
                    "Incorrect family password."
                )
            )


        # =================================================
        # FIND PERSONAL USER
        # =================================================

        user = connection.execute(
            """
            SELECT
                id,
                name,
                password_hash

            FROM users

            WHERE username = ?
            """,
            (username,)
        ).fetchone()


        # =================================================
        # CREATE USER IF NEW
        # =================================================

        if not user:

            cursor = connection.execute(
                """
                INSERT INTO users
                (
                    name,
                    username,
                    password_hash,
                    created_at
                )

                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    username,
                    generate_password_hash(
                        password
                    ),
                    datetime.now()
                )
            )

            user_id = cursor.lastrowid


        else:

            user_id = user["id"]


            if not check_password_hash(
                user["password_hash"],
                password
            ):

                connection.close()

                return render_template(
                    "join_family.html",
                    error=(
                        "Incorrect "
                        "personal password."
                    )
                )


        # =================================================
        # CHECK EXISTING MEMBERSHIP
        # =================================================

        membership = connection.execute(
            """
            SELECT
                id,
                status

            FROM family_members

            WHERE family_id = ?

            AND user_id = ?
            """,
            (
                family["id"],
                user_id
            )
        ).fetchone()


        if membership:

            connection.close()


            if membership["status"] == "approved":

                return render_template(
                    "join_family.html",
                    error=(
                        "You are already "
                        "a member of this family."
                    )
                )


            if membership["status"] == "pending":

                return render_template(
                    "join_family.html",
                    error=(
                        "Your request "
                        "is already pending."
                    )
                )


        # =================================================
        # CREATE JOIN REQUEST
        # =================================================

        connection.execute(
            """
            INSERT INTO family_members
            (
                family_id,
                user_id,
                role,
                status,
                is_sharing,
                created_at
            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                family["id"],
                user_id,
                "member",
                "pending",
                0,
                datetime.now()
            )
        )


        connection.commit()

        connection.close()


        return render_template(
            "join_family.html",
            error=(
                "✅ Join request sent successfully. "
                "Wait for the family administrator "
                "to approve you."
            )
        )


    return render_template(
        "join_family.html"
    )


# =========================================================
# APPROVE JOIN REQUEST
# =========================================================

@app.route(
    "/approve-request/<int:request_id>",
    methods=["POST"]
)
def approve_request(request_id):

    user_id = session.get("user_id")
    family_id = session.get("family_id")

    if not user_id or not family_id:

        return jsonify({
            "message": "Unauthorized"
        }), 401


    # Make sure the logged-in user is
    # actually the administrator of this family.

    if not is_family_admin(
        user_id,
        family_id
    ):

        return jsonify({
            "message": "Admin access required."
        }), 403


    connection = get_db()


    connection.execute(
        """
        UPDATE family_members

        SET status = 'approved'

        WHERE id = ?

        AND family_id = ?

        AND status = 'pending'
        """,
        (
            request_id,
            family_id
        )
    )


    connection.commit()

    connection.close()


    return redirect(
        url_for("family_dashboard")
    )

# =========================================================
# REJECT JOIN REQUEST
# =========================================================

@app.route(
    "/reject-request/<int:request_id>",
    methods=["POST"]
)
def reject_request(request_id):

    user_id = session.get("user_id")
    family_id = session.get("family_id")

    if not user_id or not family_id:

        return jsonify({
            "message": "Unauthorized"
        }), 401


    if not is_family_admin(
        user_id,
        family_id
    ):

        return jsonify({
            "message": "Admin access required."
        }), 403


    connection = get_db()


    connection.execute(
        """
        DELETE FROM family_members

        WHERE id = ?

        AND family_id = ?

        AND status = 'pending'
        """,
        (
            request_id,
            family_id
        )
    )


    connection.commit()

    connection.close()


    return redirect(
        url_for("family_dashboard")
    )
# =========================================================
# REMOVE FAMILY MEMBER
# =========================================================

@app.route(
    "/remove-member/<int:member_id>",
    methods=["POST"]
)
def remove_member(member_id):

    user_id = session.get("user_id")
    family_id = session.get("family_id")

    if not user_id or not family_id:

        return jsonify({
            "message": "Unauthorized"
        }), 401


    # -----------------------------------------------------
    # Make sure current user is admin of CURRENT family
    # -----------------------------------------------------

    if not is_family_admin(
        user_id,
        family_id
    ):

        return jsonify({
            "message": "Admin access required."
        }), 403


    connection = get_db()


    # -----------------------------------------------------
    # Never allow admin to remove themselves
    # -----------------------------------------------------

    member = connection.execute(
        """
        SELECT
            user_id,
            role
        FROM family_members

        WHERE id = ?

        AND family_id = ?
        """,
        (
            member_id,
            family_id
        )
    ).fetchone()


    if not member:

        connection.close()

        return jsonify({
            "message": "Member not found."
        }), 404


    if member["user_id"] == user_id:

        connection.close()

        return jsonify({
            "message": "The family administrator cannot remove themselves."
        }), 400


    # -----------------------------------------------------
    # Remove membership
    # -----------------------------------------------------

    connection.execute(
        """
        DELETE FROM family_members

        WHERE id = ?

        AND family_id = ?
        """,
        (
            member_id,
            family_id
        )
    )


    connection.commit()

    connection.close()


    return redirect(
        url_for("family_dashboard")
    )


# =========================================================
# MEMBER LOGIN
# =========================================================

@app.route(
    "/member-login",
    methods=["GET", "POST"]
)
def member_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        connection = get_db()


        user = connection.execute(
            """
            SELECT
                id,
                name,
                password_hash

            FROM users

            WHERE username = ?
            """,
            (username,)
        ).fetchone()


        connection.close()


        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session.clear()

            session["user_id"] = user["id"]

            session["user_name"] = user["name"]

            session["user_type"] = "member"


            return redirect(
                url_for("my_families")
            )


        return render_template(
            "member_login.html",
            error=(
                "Incorrect username "
                "or password."
            )
        )


    return render_template(
        "member_login.html"
    )


# =========================================================
# FAMILY SELECTION PAGE
# =========================================================

@app.route("/my-families")
def my_families():

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return redirect(
            url_for("member_login")
        )


    connection = get_db()


    families = connection.execute(
        """
        SELECT
            families.id,
            families.family_name,
            families.family_username,
            family_members.role,
            family_members.status

        FROM family_members

        JOIN families
            ON families.id =
               family_members.family_id

        WHERE family_members.user_id = ?

        AND family_members.status =
            'approved'

        ORDER BY families.family_name
        """,
        (user_id,)
    ).fetchall()


    connection.close()


    return render_template(
        "my_families.html",
        families=families
    )


# =========================================================
# FAMILY LIST API
# Used by "Switch Family"
# =========================================================

@app.route("/my-families-data")
def my_families_data():

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return jsonify({
            "message": "Unauthorized"
        }), 401


    connection = get_db()


    families = connection.execute(
        """
        SELECT
            families.id,
            families.family_name,
            families.family_username,
            family_members.role

        FROM family_members

        JOIN families
            ON families.id =
               family_members.family_id

        WHERE family_members.user_id = ?

        AND family_members.status =
            'approved'

        ORDER BY families.family_name
        """,
        (user_id,)
    ).fetchall()


    connection.close()


    result = []


    for family in families:

        result.append({

            "id": family["id"],

            "family_name":
                family["family_name"],

            "family_username":
                family["family_username"],

            "role":
                family["role"]

        })


    return jsonify(result)


# =========================================================
# SELECT FAMILY
# =========================================================

@app.route(
    "/select-family/<int:family_id>"
)
def select_family(family_id):

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return redirect(
            url_for("member_login")
        )


    connection = get_db()


    membership = connection.execute(
        """
        SELECT
            family_id

        FROM family_members

        WHERE family_id = ?

        AND user_id = ?

        AND status = 'approved'
        """,
        (
            family_id,
            user_id
        )
    ).fetchone()


    connection.close()


    if not membership:

        return (
            "You are not an approved "
            "member of this family.",
            403
        )


    session["family_id"] = family_id


    return redirect(
        url_for("member_home")
    )
# =========================================================
# CHECK CURRENT FAMILY ADMIN STATUS
# =========================================================

@app.route("/is-current-family-admin")
def is_current_family_admin():

    user_id = session.get("user_id")
    family_id = session.get("family_id")

    if not user_id or not family_id:

        return jsonify({
            "is_admin": False
        })

    return jsonify({
        "is_admin": is_family_admin(
            user_id,
            family_id
        )
    })


# =========================================================
# MEMBER HOME
# =========================================================

@app.route("/member-home")
def member_home():

    if not session.get("user_id"):

        return redirect(
            url_for("member_login")
        )


    if not session.get("family_id"):

        return redirect(
            url_for("my_families")
        )


    return render_template(
        "index.html",
        member_name=session.get(
            "user_name"
        )

    )
# =========================================================
# OPEN FAMILY ADMIN DASHBOARD
# =========================================================

@app.route("/open-admin-dashboard")
def open_admin_dashboard():

    user_id = session.get("user_id")
    family_id=session.get("family_id")

    if not user_id:
        return redirect(
            url_for("member_login")
        )

    if not is_family_admin(
        user_id,
        family_id
    ):
        return "You are not the administrator of this family.", 403

    # User is genuinely the admin of the selected family.
    session["user_type"] = "family_admin"

    return redirect(
        url_for("family_dashboard")
    )



# =========================================================
# START LOCATION SHARING
# =========================================================

@app.route(
    "/start-sharing",
    methods=["POST"]
)
def start_sharing():

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return jsonify({
            "message": "Please login first."
        }), 401


    connection = get_db()


    connection.execute(
        """
        UPDATE family_members

        SET is_sharing = 1

        WHERE user_id = ?

        AND status = 'approved'
        """,
        (user_id,)
    )


    connection.commit()

    connection.close()


    return jsonify({
        "message":
            "Location sharing started."
    })


# =========================================================
# STOP LOCATION SHARING
# =========================================================

@app.route(
    "/stop-sharing",
    methods=["POST"]
)
def stop_sharing():

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return jsonify({
            "message": "Please login first."
        }), 401


    connection = get_db()


    connection.execute(
        """
        UPDATE family_members

        SET is_sharing = 0

        WHERE user_id = ?
        """,
        (user_id,)
    )


    connection.commit()

    connection.close()


    return jsonify({
        "message":
            "Location sharing stopped."
    })


# =========================================================
# SHARING STATUS
# =========================================================

@app.route("/sharing-status")
def sharing_status():

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return jsonify({
            "is_sharing": False
        })


    connection = get_db()


    result = connection.execute(
        """
        SELECT COUNT(*) AS count

        FROM family_members

        WHERE user_id = ?

        AND status = 'approved'

        AND is_sharing = 1
        """,
        (user_id,)
    ).fetchone()


    connection.close()


    return jsonify({
        "is_sharing":
            result["count"] > 0
    })


# =========================================================
# SAVE LOCATION
# =========================================================

@app.route(
    "/save-location",
    methods=["POST"]
)
def save_location():

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return jsonify({
            "message":
                "No member logged in."
        }), 401


    data = request.get_json()


    if not data:

        return jsonify({
            "message":
                "No location data received."
        }), 400


    latitude = data.get(
        "latitude"
    )

    longitude = data.get(
        "longitude"
    )


    if latitude is None or longitude is None:

        return jsonify({
            "message":
                "Latitude and longitude "
                "are required."
        }), 400


    connection = get_db()


    # -----------------------------------------------------
    # Check sharing status
    # -----------------------------------------------------

    sharing = connection.execute(
        """
        SELECT COUNT(*) AS count

        FROM family_members

        WHERE user_id = ?

        AND status = 'approved'

        AND is_sharing = 1
        """,
        (user_id,)
    ).fetchone()


    if sharing["count"] == 0:

        connection.close()

        return jsonify({
            "message":
                "Location sharing is OFF."
        }), 403


    # -----------------------------------------------------
    # Save location
    # -----------------------------------------------------

    connection.execute(
        """
        INSERT INTO locations
        (
            user_id,
            latitude,
            longitude,
            timestamp
        )

        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            latitude,
            longitude,
            datetime.now()
        )
    )


    connection.commit()

    connection.close()


    return jsonify({
        "message":
            "Location saved successfully."
    })


# =========================================================
# LATEST LOCATION
# =========================================================

@app.route("/latest-location")
def latest_location():

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return jsonify({
            "message": "Unauthorized"
        }), 401


    connection = get_db()


    location = connection.execute(
        """
        SELECT
            latitude,
            longitude,
            timestamp

        FROM locations

        WHERE user_id = ?

        ORDER BY id DESC

        LIMIT 1
        """,
        (user_id,)
    ).fetchone()


    connection.close()


    if location:

        return jsonify({

            "latitude":
                location["latitude"],

            "longitude":
                location["longitude"],

            "timestamp":
                location["timestamp"]

        })


    return jsonify({
        "message":
            "No location available."
    })


# =========================================================
# ALL LOCATIONS FOR SELECTED FAMILY
# =========================================================

@app.route("/all-locations")
def all_locations():

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return jsonify({
            "message": "Unauthorized"
        }), 401


    family_id = session.get(
        "family_id"
    )


    if not family_id:

        return jsonify({
            "message":
                "No family selected."
        }), 400


    connection = get_db()


    # =====================================================
    # VERIFY MEMBERSHIP
    # =====================================================

    membership = connection.execute(
        """
        SELECT id

        FROM family_members

        WHERE family_id = ?

        AND user_id = ?

        AND status = 'approved'
        """,
        (
            family_id,
            user_id
        )
    ).fetchone()


    if not membership:

        connection.close()

        return jsonify({
            "message":
                "You are not a member "
                "of this family."
        }), 403


    # =====================================================
    # GET FAMILY MEMBERS + LATEST LOCATIONS
    # =====================================================

    members = connection.execute(
        """
        SELECT

            users.id AS user_id,

            users.name,

            family_members.is_sharing,

            locations.latitude,

            locations.longitude,

            locations.timestamp

        FROM family_members

        JOIN users
            ON users.id =
               family_members.user_id

        LEFT JOIN locations
            ON locations.user_id =
               users.id

            AND locations.id = (

                SELECT MAX(l2.id)

                FROM locations AS l2

                WHERE l2.user_id =
                      users.id

            )

        WHERE family_members.family_id = ?

        AND family_members.status =
            'approved'

        ORDER BY users.name
        """,
        (family_id,)
    ).fetchall()


    connection.close()


    result = []


    for member in members:

        # -------------------------------------------------
        # Sharing ON
        # -------------------------------------------------

        if member["is_sharing"]:

            latitude = member["latitude"]

            longitude = member["longitude"]

            timestamp = member["timestamp"]


        # -------------------------------------------------
        # Sharing OFF
        # -------------------------------------------------

        else:

            latitude = None

            longitude = None

            timestamp = None


        result.append({

            "member_id":
                member["user_id"],

            "name":
                member["name"],

            "latitude":
                latitude,

            "longitude":
                longitude,

            "timestamp":
                timestamp,

            "is_sharing":
                bool(
                    member["is_sharing"]
                )

        })


    return jsonify(result)


# =========================================================
# MEMBER LOGOUT
# =========================================================

@app.route("/member-logout")
def member_logout():

    session.clear()

    return redirect(
        url_for("member_login")
    )


# =========================================================
# GENERAL LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("member_login")
    )


# =========================================================
# RUN APPLICATION
# =========================================================
create_database()

if __name__ == "__main__":

   

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        ssl_context="adhoc"
    )