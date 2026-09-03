import os
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, inspect, text
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


ADMIN_USER = os.environ.get(
    "ADMIN_USERNAME",
    "admin"
)

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

    customer = Column(
        String(120),
        nullable=False
    )

    age = Column(
        Integer,
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

    assigned_worker_id = Column(
        Integer,
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

    @property
    def application_code(self):
        return f"HM/DS{self.id:02d}"


class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True
    )

    mobile = Column(
        String(20),
        unique=True,
        nullable=False
    )

    password_hash = Column(
        String(255),
        nullable=True
    )

    role = Column(
        String(20),
        nullable=False
    )

    name = Column(
        String(120),
        nullable=True
    )

    age = Column(
        Integer,
        nullable=True
    )

    csc_id = Column(
        String(50),
        unique=True,
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

    admin_level = Column(
        String(20),
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


# पुराने database में जरूरी columns जोड़ना

inspector = inspect(engine)

user_columns = {
    col["name"]
    for col in inspector.get_columns("users")
}

request_columns = {
    col["name"]
    for col in inspector.get_columns("requests")
}


if "password_hash" not in user_columns:
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"
            )
        )


if "assigned_worker_id" not in request_columns:
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE requests ADD COLUMN assigned_worker_id INTEGER"
            )
        )


for column_name, column_type in {
    "state": "VARCHAR(100)",
    "district": "VARCHAR(100)"
}.items():

    if column_name not in request_columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"ALTER TABLE requests ADD COLUMN {column_name} {column_type}"
                )
            )


user_columns = {
    col["name"]
    for col in inspect(engine).get_columns("users")
}


for column_name, column_type in {
    "admin_level": "VARCHAR(20)",
    "state": "VARCHAR(100)",
    "district": "VARCHAR(100)",
    "parent_admin_id": "INTEGER"
}.items():

    if column_name not in user_columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
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
        d.get("state", "").strip(),
        d.get("district", "").strip(),
        d.get("service", "").strip(),
        d.get("address", "").strip(),
        d.get("details", "").strip()
    ]

    if not all(vals):

        flash(
            "कृपया सभी जानकारी भरें",
            "error"
        )

        return redirect(
            url_for("home")
        )

    try:

        age = int(vals[1])

    except ValueError:

        flash(
            "कृपया सही उम्र डालें",
            "error"
        )

        return redirect(
            url_for("home")
        )

    new_request = RequestItem(
        customer=vals[0],
        age=age,
        phone=vals[2],
        state=vals[3],
        district=vals[4],
        service=vals[5],
        address=vals[6],
        details=vals[7]
    )

    DB.add(new_request)
    DB.commit()

    flash(
        f"आपका आवेदन सफलतापूर्वक भेज दिया गया है। Application ID: #{new_request.id}",
        "success"
    )

    return redirect(
        url_for(
            "check_status",
            phone=vals[2]
        )
    )


@app.route(
    "/worker/register",
    methods=["GET", "POST"]
)
def worker_register():

    if request.method == "GET":

        return render_template(
            "worker_register.html"
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

    csc_id = request.form.get(
        "csc_id",
        ""
    ).strip() or None

    center_name = request.form.get(
        "center_name",
        ""
    ).strip() or None

    address = request.form.get(
        "address",
        ""
    ).strip()


    if not name or not mobile or not password or not address:

        flash(
            "कृपया सभी जरूरी जानकारी भरें",
            "error"
        )

        return redirect(
            url_for("worker_register")
        )


    if not mobile.isdigit() or len(mobile) != 10:

        flash(
            "कृपया सही 10 अंकों का मोबाइल नंबर डालें",
            "error"
        )

        return redirect(
            url_for("worker_register")
        )


    if len(password) < 6:

        flash(
            "पासवर्ड कम से कम 6 अक्षर का होना चाहिए",
            "error"
        )

        return redirect(
            url_for("worker_register")
        )


    if DB.query(User).filter(
        User.mobile == mobile
    ).first():

        flash(
            "यह मोबाइल नंबर पहले से Registered है",
            "error"
        )

        return redirect(
            url_for("worker_register")
        )


    if csc_id and DB.query(User).filter(
        User.csc_id == csc_id
    ).first():

        flash(
            "यह CSC ID पहले से Registered है",
            "error"
        )

        return redirect(
            url_for("worker_register")
        )


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

    DB.add(worker)
    DB.commit()


    flash(
        "Registration सफल हुआ। Admin approval के बाद आप Login कर सकेंगे।",
        "success"
    )

    return redirect(
        url_for("worker_register")
    )


@app.get("/admin")
def admin():

    if not session.get("admin"):

        return render_template(
            "login.html"
        )


    admin_user = None

    if session.get("admin_user_id"):

        admin_user = DB.get(
            User,
            session.get("admin_user_id")
        )


    if admin_user and admin_user.admin_level == "state":

        requests = (
            DB.query(RequestItem)
            .filter(
                RequestItem.state == admin_user.state
            )
            .order_by(
                RequestItem.id.desc()
            )
            .all()
        )

    elif admin_user and admin_user.admin_level == "district":

        requests = (
            DB.query(RequestItem)
            .filter(
                RequestItem.state == admin_user.state,
                RequestItem.district == admin_user.district
            )
            .order_by(
                RequestItem.id.desc()
            )
            .all()
        )

    else:

        requests = (
            DB.query(RequestItem)
            .order_by(
                RequestItem.id.desc()
            )
            .all()
        )


    if admin_user and admin_user.admin_level == "state":

        workers = (
            DB.query(User)
            .filter(
                User.role == "worker",
                User.state == admin_user.state
            )
            .order_by(
                User.id.desc()
            )
            .all()
        )

    elif admin_user and admin_user.admin_level == "district":

        workers = (
            DB.query(User)
            .filter(
                User.role == "worker",
                User.state == admin_user.state,
                User.district == admin_user.district
            )
            .order_by(
                User.id.desc()
            )
            .all()
        )

    else:

        workers = (
            DB.query(User)
            .filter(
                User.role == "worker"
            )
            .order_by(
                User.id.desc()
            )
            .all()
        )


    admins = (
        DB.query(User)
        .filter(
            User.role == "admin"
        )
        .order_by(
            User.id.desc()
        )
        .all()
    )


    return render_template(
        "admin.html",
        requests=requests,
        workers=workers,
        admins=admins
    )


@app.post(
    "/admin/worker/approve/<int:worker_id>"
)
def approve_worker(worker_id):

    if not session.get("admin"):

        return redirect(
            url_for("admin")
        )


    worker = DB.get(
        User,
        worker_id
    )
