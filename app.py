import os
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session


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
    connect_args={"check_same_thread": False} if url.startswith("sqlite") else {}
)

DB = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()

ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin")

ADMIN_HASH = os.environ.get(
    "ADMIN_PASSWORD_HASH",
    generate_password_hash("ChangeMe123!")
)

SERVICES = [
    "गर्भवती महिला सहायता",
    "Serious Patient",
    "Senior Citizen Assistance",
    "दिव्यांगजन सहायता",
    "Digital & Citizen Services",
    "अन्य सहायता"
]


class RequestItem(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True)
    customer = Column(String(120), nullable=False)
    age = Column(Integer, nullable=False)
    phone = Column(String(30), nullable=False)
    service = Column(String(150), nullable=False)
    address = Column(Text, nullable=False)
    details = Column(Text, nullable=False)
    assigned_worker_id = Column(Integer, nullable=True)
    
    status = Column(
        String(30),
        default="Pending",
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).replace(tzinfo=None),
        nullable=False
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    mobile = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False)
    name = Column(String(120), nullable=True)
    age = Column(Integer, nullable=True)
    csc_id = Column(String(50), unique=True, nullable=True)
    center_name = Column(String(150), nullable=True)
    address = Column(Text, nullable=True)
    latitude = Column(String(30), nullable=True)
    longitude = Column(String(30), nullable=True)

    approved = Column(
        Boolean,
        default=False,
        nullable=False
    )

    active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).replace(tzinfo=None),
        nullable=False
    )


Base.metadata.create_all(engine)

# पुराने database में नए User columns जोड़ना
from sqlalchemy import inspect, text

inspector = inspect(engine)
user_columns = {
    col["name"] for col in inspector.get_columns("users")
}

if "password_hash" not in user_columns:
    with engine.begin() as conn:
        if url.startswith("sqlite"):
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"
                )
            )
        else:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"
                )
            )
# पुराने database में assigned_worker_id column जोड़ना
request_columns = {
    col["name"] for col in inspector.get_columns("requests")
}

if "assigned_worker_id" not in request_columns:
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE requests ADD COLUMN assigned_worker_id INTEGER"
            )
        )

@app.teardown_appcontext
def close(e=None):
    DB.remove()


@app.get("/")
def home():
    return render_template(
        "index.html",
        services=SERVICES
    )


@app.post("/request-service")
def add():
    d = request.form

    vals = [
        d.get("customer", "").strip(),
        d.get("age", "").strip(),
        d.get("phone", "").strip(),
        d.get("service", "").strip(),
        d.get("address", "").strip(),
        d.get("details", "").strip()
    ]

    if not all(vals):
        flash(
            "कृपया सभी जानकारी भरें",
            "error"
        )
        return redirect(url_for("home"))

    try:
        age = int(vals[1])
    except ValueError:
        flash(
            "कृपया सही उम्र डालें",
            "error"
        )
        return redirect(url_for("home"))

    new_request = RequestItem(
        customer=vals[0],
        age=age,
        phone=vals[2],
        service=vals[3],
        address=vals[4],
        details=vals[5]
    )

    DB.add(new_request)
    DB.commit()

    application_id = new_request.id

    flash(
        f"आपका आवेदन सफलतापूर्वक भेज दिया गया है। Application ID: #{application_id}",
        "success"
    )

    return redirect(
        url_for(
            "check_status",
            phone=vals[2]
        )
    )

@app.route("/worker/register", methods=["GET", "POST"])
def worker_register():

    if request.method == "GET":
        return render_template("worker_register.html")

    name = request.form.get("name", "").strip()
    mobile = request.form.get("mobile", "").strip()
    password = request.form.get("password", "")
    csc_id = request.form.get("csc_id", "").strip() or None
    center_name = request.form.get("center_name", "").strip() or None
    address = request.form.get("address", "").strip()

    if not name or not mobile or not password or not address:
        flash(
            "कृपया सभी जरूरी जानकारी भरें",
            "error"
        )
        return redirect(url_for("worker_register"))

    if not mobile.isdigit() or len(mobile) != 10:
        flash(
            "कृपया सही 10 अंकों का मोबाइल नंबर डालें",
            "error"
        )
        return redirect(url_for("worker_register"))

    if len(password) < 6:
        flash(
            "पासवर्ड कम से कम 6 अक्षर का होना चाहिए",
            "error"
        )
        return redirect(url_for("worker_register"))

    existing_mobile = (
        DB.query(User)
        .filter(User.mobile == mobile)
        .first()
    )

    if existing_mobile:
        flash(
            "यह मोबाइल नंबर पहले से Registered है",
            "error"
        )
        return redirect(url_for("worker_register"))

    if csc_id:
        existing_csc = (
            DB.query(User)
            .filter(User.csc_id == csc_id)
            .first()
        )

        if existing_csc:
            flash(
                "यह CSC ID पहले से Registered है",
                "error"
            )
            return redirect(url_for("worker_register"))

    worker = User(
        mobile=mobile,
        password_hash=generate_password_hash(password),
        role="worker",
        name=name,
        csc_id=csc_id,
        center_name=center_name,
        address=address,
        approved=False,
        active=True
    )

    # Password अभी User model में रखने की जगह
    # आगे dedicated password field जोड़ेंगे।
    # इसलिए इस step में registration record save किया जा रहा है।

    DB.add(worker)
    DB.commit()

    flash(
        "Registration सफल हुआ। Admin approval के बाद आप Login कर सकेंगे।",
        "success"
    )

    return redirect(url_for("worker_register"))
@app.route("/admin", methods=["GET"])
def admin():
    if not session.get("admin"):
        return render_template("login.html")

    requests = (
        DB.query(RequestItem)
        .order_by(RequestItem.id.desc())
        .all()
    )

    workers = (
        DB.query(User)
        .filter(User.role == "worker")
        .order_by(User.id.desc())
        .all()
    )

    return render_template(
        "admin.html",
        requests=requests,
        workers=workers
    )


@app.post("/admin/worker/approve/<int:worker_id>")
def approve_worker(worker_id):

    if not session.get("admin"):
        return redirect(url_for("admin"))

    worker = DB.get(User, worker_id)

    if worker and worker.role == "worker":
        worker.approved = True
        worker.active = True
        DB.commit()

        flash(
            f"{worker.name} का Worker Registration Approve कर दिया गया है।",
            "success"
        )

    return redirect(url_for("admin"))
@app.post("/admin/assign/<int:rid>")
def assign_request(rid):

    if not session.get("admin"):
        return redirect(url_for("admin"))

    request_item = DB.get(RequestItem, rid)
    worker_id = request.form.get("worker_id", "").strip()

    if not request_item:
        flash("Application नहीं मिला", "error")
        return redirect(url_for("admin"))

    if not worker_id:
        request_item.assigned_worker_id = None
        request_item.status = "Pending"
        DB.commit()

        flash(
            f"Application #{rid} का Worker Assignment हटा दिया गया है।",
            "success"
        )
        return redirect(url_for("admin"))

    try:
        worker_id = int(worker_id)
    except ValueError:
        flash("Invalid Worker", "error")
        return redirect(url_for("admin"))

    worker = (
        DB.query(User)
        .filter(User.id == worker_id)
        .filter(User.role == "worker")
        .filter(User.approved == True)
        .filter(User.active == True)
        .first()
    )

    if not worker:
        flash("Valid Active Worker नहीं मिला", "error")
        return redirect(url_for("admin"))

    request_item.assigned_worker_id = worker.id
    request_item.status = "Assigned"

    DB.commit()

    flash(
        f"Application #{rid} {worker.name} को Assign कर दिया गया है।",
        "success"
    )

    return redirect(url_for("admin"))


@app.post("/admin/login")
def login():
    username = request.form.get("username")
    password = request.form.get("password", "")

    if (
        username == ADMIN_USER
        and check_password_hash(
            ADMIN_HASH,
            password
        )
    ):
        session["admin"] = True

    else:
        flash(
            "Login failed",
            "error"
        )

    return redirect(url_for("admin"))

@app.post("/admin/status/<int:rid>")
def status(rid):
    if not session.get("admin"):
        return redirect(url_for("admin"))

    x = DB.get(RequestItem, rid)
    s = request.form.get("status")

    allowed_statuses = (
        "Pending",
        "Assigned",
        "In Progress",
        "Completed",
        "Cancelled"
    )

    if x and s in allowed_statuses:
        x.status = s
        DB.commit()

    return redirect(url_for("admin"))


@app.get("/status")
def check_status():
    phone = request.args.get(
        "phone",
        ""
    ).strip()

    if not phone:
        return render_template(
            "status.html",
            requests=[]
        )

    requests = (
        DB.query(RequestItem)
        .filter(RequestItem.phone == phone)
        .order_by(RequestItem.id.desc())
        .all()
    )

    return render_template(
        "status.html",
        requests=requests
    )


@app.post("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("admin"))

# ==============================
# WORKER LOGIN & DASHBOARD
# ==============================

@app.route("/worker/login", methods=["GET", "POST"])
def worker_login():

    if request.method == "GET":
        return render_template("worker_login.html")

    mobile = request.form.get("mobile", "").strip()
    password = request.form.get("password", "")

    if not mobile or not password:
        flash(
            "कृपया Mobile और Password भरें",
            "error"
        )
        return redirect(url_for("worker_login"))

    worker = (
        DB.query(User)
        .filter(User.mobile == mobile)
        .filter(User.role == "worker")
        .first()
    )

    if not worker:
        flash(
            "Worker account नहीं मिला",
            "error"
        )
        return redirect(url_for("worker_login"))

    if not worker.approved:
        flash(
            "आपका Registration अभी Admin approval के लिए Pending है",
            "error"
        )
        return redirect(url_for("worker_login"))

    if not worker.active:
        flash(
            "आपका Worker account अभी Active नहीं है",
            "error"
        )
        return redirect(url_for("worker_login"))

    if not worker.password_hash or not check_password_hash(
        worker.password_hash,
        password
    ):
        flash(
            "Mobile या Password गलत है",
            "error"
        )
        return redirect(url_for("worker_login"))

    session.clear()

    session["worker_id"] = worker.id
    session["worker"] = True

    flash(
        "Worker Login सफल हुआ",
        "success"
    )

    return redirect(url_for("worker_dashboard"))


@app.get("/worker/dashboard")
def worker_dashboard():

    if not session.get("worker"):
        return redirect(url_for("worker_login"))

    worker_id = session.get("worker_id")

    worker = DB.get(User, worker_id)

    if not worker or worker.role != "worker":
        session.clear()
        return redirect(url_for("worker_login"))

    requests = (
        DB.query(RequestItem)
        .order_by(RequestItem.id.desc())
        .all()
    )

    return render_template(
        "worker_dashboard.html",
        worker=worker,
        requests=requests
    )


@app.post("/worker/logout")
def worker_logout():

    session.clear()

    return redirect(url_for("worker_login"))

@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )
    )
