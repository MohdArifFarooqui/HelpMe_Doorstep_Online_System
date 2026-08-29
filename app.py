import os
from datetime import datetime
from zoneinfo import ZoneInfo 
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","change-this-secret-key")
url=os.environ.get("DATABASE_URL","sqlite:///helpme_doorstep.db")
if url.startswith("postgres://"): url=url.replace("postgres://","postgresql://",1)
engine=create_engine(url,connect_args={"check_same_thread":False} if url.startswith("sqlite") else {})
DB=scoped_session(sessionmaker(bind=engine)); Base=declarative_base()
ADMIN_USER=os.environ.get("ADMIN_USERNAME","admin")
ADMIN_HASH=os.environ.get("ADMIN_PASSWORD_HASH",generate_password_hash("ChangeMe123!"))
SERVICES=["गर्भवती महिला सहायता","Senior Citizen Assistance","दिव्यांगजन सहायता","Digital & Citizen Services","अन्य सहायता"]
class RequestItem(Base):
    __tablename__="requests"
    id=Column(Integer,primary_key=True); customer=Column(String(120),nullable=False);age=Column(Integer,nullable=False); phone=Column(String(30),nullable=False)
    service=Column(String(150),nullable=False); address=Column(Text,nullable=False); details=Column(Text,nullable=False)
    status=Column(String(30),default="Pending",nullable=False); created_at=Column(DateTime,default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")),nullable=False)
Base.metadata.create_all(engine)
@app.teardown_appcontext
def close(e=None): DB.remove()
@app.get("/")
def home(): return render_template("index.html",services=SERVICES)
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
        flash("कृपया सभी जानकारी भरें", "error")
        return redirect(url_for("home"))

    DB.add(RequestItem(
        customer=vals[0],
        age=int(vals[1]),
        phone=vals[2],
        service=vals[3],
        address=vals[4],
        details=vals[5]
    ))
    DB.commit()

    flash("आपका सेवा अनुरोध सफलतापूर्वक भेज दिया गया है।", "success")
    return redirect(url_for("home"))
@app.route("/admin",methods=["GET"])
def admin():
    if not session.get("admin"): return render_template("login.html")
    return render_template("admin.html",requests=DB.query(RequestItem).order_by(RequestItem.id.desc()).all())
@app.post("/admin/login")
def login():
    if request.form.get("username")==ADMIN_USER and check_password_hash(ADMIN_HASH,request.form.get("password","")):
        session["admin"]=True
    else: flash("Login failed","error")
    return redirect(url_for("admin"))
@app.post("/admin/status/<int:rid>")
def status(rid):
    if not session.get("admin"):
        return redirect(url_for("admin"))

    x = DB.get(RequestItem, rid)
    s = request.form.get("status")

    if x and s in ("Pending", "Assigned", "In Progress", "Completed", "Cancelled"):
        x.status = s
        DB.commit()

    return redirect(url_for("admin"))
@app.get("/status")
def check_status():
    phone = request.args.get("phone", "").strip()

    if not phone:
        return render_template("status.html", requests=[])

    requests = DB.query(RequestItem).filter(
        RequestItem.phone == phone
    ).order_by(RequestItem.id.desc()).all()

    return render_template("status.html", requests=requests)
@app.post("/admin/logout")
def logout(): session.clear(); return redirect(url_for("admin"))
@app.get("/health")
def health(): return {"status":"ok"}
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
