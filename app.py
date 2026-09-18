import os
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    text, 
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session


# =========================================================
# APP CONFIG
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key"
)

url = os.environ.get(
    "DATABASE_URL",
    "sqlite:///helpme_doorstep.db"
)

if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    url,
    connect_args={"check_same_thread": False}
    if url.startswith("sqlite")
    else {},
)

DB = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()


# =========================================================
# MAIN ADMIN
# =========================================================

ADMIN_USER = os.environ.get(
    "ADMIN_USERNAME",
    "admin"
)

ADMIN_HASH = os.environ.get(
    "ADMIN_PASSWORD_HASH",
    generate_password_hash("ChangeMe123!")
)


# =========================================================
# SERVICES
# =========================================================

SERVICES = [
    "गर्भवती महिला सहायता",
    "Senior Citizen Assistance",
    "दिव्यांगजन सहायता",
    "Digital & Citizen Services",
    "अन्य सहायता",
]


# =========================================================
# REQUEST MODEL
# =========================================================

class RequestItem(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True)

    customer = Column(
        String(120),
        nullable=False
    )

    phone = Column(
        String(30),
        nullable=False
    )

    service = Column(
        String(150),
        nullable=False
    )

    address = Column(
        Text,
        nullable=False
    )

    details = Column(
        Text,
        nullable=False
    )

    age = Column(
        Integer,
        nullable=True
    )

    assigned_worker_id = Column(
        Integer,
        nullable=True
    )

    status = Column(
        String(30),
        default="Pending",
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.now,
        nullable=False
    )


# =========================================================
# USER MODEL
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True
    )

    mobile = Column(
        String(20),
        nullable=True
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    role = Column(
        String(30),
        nullable=False
    )

    name = Column(
        String(120),
        nullable=False
    )

    age = Column(
        Integer,
        nullable=True
    )

    csc_id = Column(
        String(50),
        nullable=True
    )

    center_name = Column(
        String(150),
        nullable=True
    )

    address = Column(
        Text,
        nullable=True
    )

    latitude = Column(
        String(30),
        nullable=True
    )

    longitude = Column(
        String(30),
        nullable=True
    )

    state = Column(
        String(100),
        nullable=True
    )

    district = Column(
        String(100),
        nullable=True
    )

    parent_admin_id = Column(
        Integer,
        nullable=True
    )

    admin_code = Column(
        String(50),
        nullable=True
    )

    approved = Column(
        Integer,
        default=0
    )

    active = Column(
        Integer,
        default=1
    )

    created_at = Column(
        DateTime,
        default=datetime.now
    )


# =========================================================
# CREATE TABLES
# =========================================================

Base.metadata.create_all(engine)


# =========================================================
# SAFE SQLITE MIGRATION
# =========================================================

def migrate_database():
    """
    Existing SQLite database ko delete kiye bina
    required columns add karta hai.
    """

    if not url.startswith("sqlite"):
        return

    with engine.begin() as conn:

        # requests table
        request_columns = {
            row[1]
            for row in conn.execute(
                text("PRAGMA table_info(requests)")
            )
        }

        if "age" not in request_columns:
            conn.execute(
                text(
                    "ALTER TABLE requests "
                    "ADD COLUMN age INTEGER"
                )
            )

        if "assigned_worker_id" not in request_columns:
            conn.execute(
                text(
                    "ALTER TABLE requests "
                    "ADD COLUMN assigned_worker_id INTEGER"
                )
            )

        # users table
        user_columns = {
            row[1]
            for row in conn.execute(
                text("PRAGMA table_info(users)")
            )
        }

        if "admin_code" not in user_columns:
            conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN admin_code VARCHAR(50)"
                )
            )


migrate_database()


# =========================================================
# HELPERS
# =========================================================

def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    return DB.get(User, user_id)


def admin_logged_in():
    return session.get("admin") is True


def valid_status(status_value):
    return status_value in {
        "Pending",
        "Assigned",
        "In Progress",
        "Completed",
        "Cancelled",
    }


def generate_admin_code(role):
    """
    State/District Admin ke liye unique code.
    """

    prefix = {
        "state_admin": "HMDS/SA",
        "district_admin": "HMDS/DA",
    }.get(role)

    if not prefix:
        return None

    users = (
        DB.query(User)
        .filter(User.role == role)
        .all()
    )

    numbers = []

    for user in users:
        code = user.admin_code or ""

        if code.startswith(prefix + "/"):
            try:
                number = int(
                    code.split("/")[-1]
                )
                numbers.append(number)
            except ValueError:
                pass

    next_number = (
        max(numbers) + 1
        if numbers
        else 1
    )

    if role == "state_admin":
        return f"HMDS/SA/{next_number:02d}"

    return f"HMDS/DA{next_number:02d}"


# =========================================================
# DATABASE CLEANUP
# =========================================================

@app.teardown_appcontext
def close(error=None):
    DB.remove()


# =========================================================
# CUSTOMER HOME
# =========================================================

@app.get("/")
def home():
    return render_template(
        "index.html",
        services=SERVICES
    )


# =========================================================
# CUSTOMER REQUEST
# =========================================================

@app.post("/request-service")
def add():

    d = request.form

    customer = d.get(
        "customer",
        ""
    ).strip()

    phone = d.get(
        "phone",
        ""
    ).strip()

    service = d.get(
        "service",
        ""
    ).strip()

    address = d.get(
        "address",
        ""
    ).strip()

    details = d.get(
        "details",
        ""
    ).strip()

    age_text = d.get(
        "age",
        ""
    ).strip()

    if not all([
        customer,
        phone,
        service,
        address,
        details,
    ]):
        flash(
            "कृपया सभी जानकारी भरें।",
            "error"
        )
        return redirect(
            url_for("home")
        )

    age = None

    if age_text:
        try:
            age = int(age_text)
        except ValueError:
            age = None

    DB.add(
        RequestItem(
            customer=customer,
            phone=phone,
            service=service,
            address=address,
            details=details,
            age=age,
            status="Pending",
        )
    )

    DB.commit()

    flash(
        "आपका सेवा अनुरोध सफलतापूर्वक भेज दिया गया है।",
        "success"
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# MAIN ADMIN LOGIN PAGE
# =========================================================

@app.route(
    "/admin",
    methods=["GET"]
)
def admin():

    if not admin_logged_in():
        return render_template(
            "login.html"
        )

    requests_list = (
        DB.query(RequestItem)
        .order_by(
            RequestItem.id.desc()
        )
        .all()
    )

    workers = (
        DB.query(User)
        .filter(
            User.role == "worker",
            User.active == 1
        )
        .order_by(
            User.name.asc()
        )
        .all()
    )

    state_admins = (
        DB.query(User)
        .filter(
            User.role == "state_admin"
        )
        .order_by(
            User.id.desc()
        )
        .all()
    )

    district_admins = (
        DB.query(User)
        .filter(
            User.role == "district_admin"
        )
        .order_by(
            User.id.desc()
        )
        .all()
    )

    all_users = (
        DB.query(User)
        .order_by(
            User.id.desc()
        )
        .all()
    )

    return render_template(
        "admin.html",
        requests=requests_list,
        workers=workers,
        state_admins=state_admins,
        district_admins=district_admins,
        all_users=all_users,
    )


# =========================================================
# MAIN ADMIN LOGIN
# =========================================================

@app.post("/admin/login")
def login():

    username = request.form.get(
        "username",
        ""
    )

    password = request.form.get(
        "password",
        ""
    )

    if (
            username == ADMIN_USER
            and check_password_hash(
        ADMIN_HASH,
        password
    )
    ):
        session.clear()
        session["admin"] = True
        session["admin_role"] = "main_admin"

    else:
        flash(
            "Login failed",
            "error"
        )

    return redirect(
        url_for("admin")
    )


# =========================================================
# ASSIGN WORKER
# =========================================================

@app.post(
    "/admin/assign/<int:rid>"
)
def assign_worker(rid):

    if not admin_logged_in():
        return redirect(
            url_for("admin")
        )

    item = DB.get(
        RequestItem,
        rid
    )

    worker_id_text = request.form.get(
        "worker_id",
        ""
    )

    if not item:
        flash(
            "Request नहीं मिला।",
            "error"
        )
        return redirect(
            url_for("admin")
        )

    try:
        worker_id = int(
            worker_id_text
        )
    except ValueError:
        flash(
            "Invalid worker.",
            "error"
        )
        return redirect(
            url_for("admin")
        )

    worker = (
        DB.query(User)
        .filter(
            User.id == worker_id,
            User.role == "worker",
            User.active == 1
        )
        .first()
    )

    if not worker:
        flash(
            "Active worker नहीं मिला।",
            "error"
        )
        return redirect(
            url_for("admin")
        )

    item.assigned_worker_id = worker.id
    item.status = "Assigned"

    DB.commit()

    flash(
        f"Request #{rid} worker {worker.name} को assign कर दी गई।",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# REQUEST STATUS
# =========================================================

@app.post(
    "/admin/status/<int:rid>"
)
def status(rid):

    if not admin_logged_in():
        return redirect(
            url_for("admin")
        )

    item = DB.get(
        RequestItem,
        rid
    )

    new_status = request.form.get(
        "status",
        ""
    )

    if (
            item
            and valid_status(new_status)
    ):
        item.status = new_status
        DB.commit()

    return redirect(
        url_for("admin")
    )


# =========================================================
# CREATE STATE ADMIN
# =========================================================

@app.post(
    "/admin/create-state-admin"
)
def create_state_admin():

    if not admin_logged_in():
        return redirect(
            url_for("admin")
        )

    name = request.form.get(
        "name",
        ""
    ).strip()

    mobile = request.form.get(
        "mobile",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    state = request.form.get(
        "state",
        ""
    ).strip()

    if not name or not mobile or not password:
        flash(
            "Name, mobile और password जरूरी हैं।",
            "error"
        )
        return redirect(
            url_for("admin")
        )

    code = generate_admin_code(
        "state_admin"
    )

    user = User(
        name=name,
        mobile=mobile,
        password_hash=generate_password_hash(
            password
        ),
        role="state_admin",
        state=state,
        admin_code=code,
        approved=1,
        active=1,
    )

    DB.add(user)
    DB.commit()

    flash(
        f"State Admin बनाया गया। Admin Code: {code}",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# CREATE DISTRICT ADMIN
# =========================================================

@app.post(
    "/admin/create-district-admin"
)
def create_district_admin():

    if not admin_logged_in():
        return redirect(
            url_for("admin")
        )

    name = request.form.get(
        "name",
        ""
    ).strip()

    mobile = request.form.get(
        "mobile",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    state = request.form.get(
        "state",
        ""
    ).strip()

    district = request.form.get(
        "district",
        ""
    ).strip()

    if not name or not mobile or not password:
        flash(
            "Name, mobile और password जरूरी हैं।",
            "error"
        )
        return redirect(
            url_for("admin")
        )

    code = generate_admin_code(
        "district_admin"
    )

    user = User(
        name=name,
        mobile=mobile,
        password_hash=generate_password_hash(
            password
        ),
        role="district_admin",
        state=state,
        district=district,
        admin_code=code,
        approved=1,
        active=1,
    )

    DB.add(user)
    DB.commit()

    flash(
        f"District Admin बनाया गया। Admin Code: {code}",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# CREATE WORKER
# =========================================================

@app.post(
    "/admin/create-worker"
)
def create_worker():

    if not admin_logged_in():
        return redirect(
            url_for("admin")
        )

    name = request.form.get(
        "name",
        ""
    ).strip()

    mobile = request.form.get(
        "mobile",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    state = request.form.get(
        "state",
        ""
    ).strip()

    district = request.form.get(
        "district",
        ""
    ).strip()

    address = request.form.get(
        "address",
        ""
    ).strip()

    if not name or not mobile or not password:
        flash(
            "Worker name, mobile और password जरूरी हैं।",
            "error"
        )
        return redirect(
            url_for("admin")
        )

    worker = User(
        name=name,
        mobile=mobile,
        password_hash=generate_password_hash(
            password
        ),
        role="worker",
        state=state,
        district=district,
        address=address,
        approved=1,
        active=1,
    )

    DB.add(worker)
    DB.commit()

    flash(
        "Worker सफलतापूर्वक बनाया गया।",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# ACTIVATE / DEACTIVATE USER
# =========================================================

@app.post(
    "/admin/toggle-user/<int:user_id>"
)
def toggle_user(user_id):

    if not admin_logged_in():
        return redirect(
            url_for("admin")
        )

    user = DB.get(
        User,
        user_id
    )

    if not user:
        flash(
            "User नहीं मिला।",
            "error"
        )
        return redirect(
            url_for("admin")
        )

    user.active = (
        0 if user.active else 1
    )

    DB.commit()

    flash(
        f"{user.name} का status update हो गया।",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# APPROVE USER
# =========================================================

@app.post(
    "/admin/approve-user/<int:user_id>"
)
def approve_user(user_id):

    if not admin_logged_in():
        return redirect(
            url_for("admin")
        )

    user = DB.get(
        User,
        user_id
    )

    if user:
        user.approved = 1
        user.active = 1
        DB.commit()

        flash(
            f"{user.name} approved है।",
            "success"
        )

    return redirect(
        url_for("admin")
    )


# =========================================================
# WORKER LOGIN
# =========================================================

@app.route(
    "/worker/login",
    methods=["GET", "POST"]
)
def worker_login():

    if request.method == "GET":
        return """
        <!doctype html>
        <html lang="hi">
        <head>
        <meta charset="utf-8">
        <meta name="viewport"
              content="width=device-width,initial-scale=1">
        <title>Worker Login - HelpMe Doorstep</title>
        <style>
        body{font-family:Arial;background:#f5f7f8;padding:40px}
        .box{max-width:420px;margin:auto;background:white;
        padding:30px;border-radius:15px}
        input,button{width:100%;padding:12px;margin:8px 0;
        box-sizing:border-box}
        button{background:#159c91;color:white;border:0;
        border-radius:8px}
        </style>
        </head>
        <body>
        <div class="box">
        <h2>HelpMe Doorstep</h2>
        <h3>Worker Login</h3>
        <form method="post">
        <input name="mobile" placeholder="Mobile Number" required>
        <input name="password" type="password"
               placeholder="Password" required>
        <button>Login</button>
        </form>
        </div>
        </body>
        </html>
        """

    mobile = request.form.get(
        "mobile",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    worker = (
        DB.query(User)
        .filter(
            User.mobile == mobile,
            User.role == "worker"
        )
        .first()
    )

    if (
            not worker
            or not worker.active
            or not worker.approved
            or not check_password_hash(
        worker.password_hash,
        password
    )
    ):
        return """
        <h2>Login failed</h2>
        <p>Mobile/password गलत है या Worker inactive/unapproved है.</p>
        <a href="/worker/login">Back to Login</a>
        """, 401

    session.clear()

    session["worker_id"] = worker.id

    return redirect(
        url_for("worker_dashboard")
    )


# =========================================================
# WORKER DASHBOARD
# =========================================================

@app.get(
    "/worker"
)
def worker_dashboard():

    worker_id = session.get(
        "worker_id"
    )

    if not worker_id:
        return redirect(
            url_for("worker_login")
        )

    worker = DB.get(
        User,
        worker_id
    )

    if (
            not worker
            or not worker.active
            or not worker.approved
    ):
        session.clear()
        return redirect(
            url_for("worker_login")
        )

    requests_list = (
        DB.query(RequestItem)
        .filter(
            RequestItem.assigned_worker_id
            == worker.id
        )
        .order_by(
            RequestItem.id.desc()
        )
        .all()
    )

    rows = ""

    for item in requests_list:

        rows += f"""
        <tr>
        <td>{item.id}</td>
        <td>{item.customer}<br>{item.phone}</td>
        <td>{item.service}</td>
        <td>{item.address}</td>
        <td>{item.status}</td>
        <td>
        <form method="post"
              action="/worker/status/{item.id}">
        <select name="status"
                onchange="this.form.submit()">
        """

        for s in [
            "Assigned",
            "In Progress",
            "Completed",
            "Cancelled",
        ]:
            selected = (
                "selected"
                if item.status == s
                else ""
            )

            rows += (
                f'<option {selected}>{s}</option>'
            )

        rows += """
        </select>
        </form>
        </td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
        <td colspan="6">
        अभी कोई assigned request नहीं है।
        </td>
        </tr>
        """

    return f"""
    <!doctype html>
    <html lang="hi">
    <head>
    <meta charset="utf-8">
    <meta name="viewport"
          content="width=device-width,initial-scale=1">
    <title>Worker Dashboard</title>
    <style>
    body{{font-family:Arial;margin:0;background:#f5f7f8}}
    header{{padding:20px;background:#159c91;color:white}}
    main{{padding:20px}}
    table{{width:100%;background:white;border-collapse:collapse}}
    th,td{{padding:12px;border:1px solid #ddd;text-align:left}}
    </style>
    </head>
    <body>
    <header>
    <h2>HelpMe Doorstep - Worker</h2>
    <p>{worker.name}</p>
    </header>
    <main>
    <table>
    <tr>
    <th>ID</th>
    <th>Customer</th>
    <th>Service</th>
    <th>Address</th>
    <th>Status</th>
    <th>Update</th>
    </tr>
    {rows}
    </table>
    </main>
    </body>
    </html>
    """


# =========================================================
# WORKER STATUS UPDATE
# =========================================================

@app.post(
    "/worker/status/<int:rid>"
)
def worker_status(rid):

    worker_id = session.get(
        "worker_id"
    )

    if not worker_id:
        return redirect(
            url_for("worker_login")
        )

    item = DB.get(
        RequestItem,
        rid
    )

    new_status = request.form.get(
        "status",
        ""
    )

    if (
            item
            and item.assigned_worker_id
            == worker_id
            and new_status in {
        "Assigned",
        "In Progress",
        "Completed",
        "Cancelled",
    }
    ):
        item.status = new_status
        DB.commit()

    return redirect(
        url_for("worker_dashboard")
    )


# =========================================================
# WORKER LOGOUT
# =========================================================

@app.post(
    "/worker/logout"
)
def worker_logout():

    session.clear()

    return redirect(
        url_for("worker_login")
    )


# =========================================================
# MAIN ADMIN LOGOUT
# =========================================================

@app.post(
    "/admin/logout"
)
def logout():

    session.clear()

    return redirect(
        url_for("admin")
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
    )