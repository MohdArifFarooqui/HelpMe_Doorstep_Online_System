# HelpMe Doorstep Online System
Customer website + Admin Panel + shared database.

Local:
1. `py -m pip install -r requirements.txt`
2. `py app.py`
3. Customer: http://127.0.0.1:5000/
4. Admin: http://127.0.0.1:5000/admin
Demo login: admin / ChangeMe123!

Online deployment:
Build: `pip install -r requirements.txt`
Start: `gunicorn app:app`
Use PostgreSQL by setting DATABASE_URL. Also set SECRET_KEY, ADMIN_USERNAME and ADMIN_PASSWORD_HASH. HTTPS and backups are required before real customer data is collected.
