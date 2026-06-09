# FRAS - Face Recognition Attendance System

FRAS is a Flask-based attendance management system that uses face recognition to register students and mark attendance. It includes student management, photo-based attendance, voice check-in, daily and monthly reports, and CSV/Excel export tools.

## Features

- Admin login and dashboard
- Student registration with face image storage
- Face recognition attendance marking
- Classroom/photo attendance processing
- Voice check-in support
- Student search, details, edit, and delete workflows
- Daily attendance report
- Monthly attendance percentage report
- CSV and Excel report exports
- Optional registration email notifications

## Tech Stack

- Python
- Flask
- MySQL
- OpenCV
- face-recognition / dlib
- NumPy
- Pillow
- openpyxl

## Project Structure

```text
FRAS/
|-- app.py                         # Main Flask application
|-- database.py                    # Database access and attendance logic
|-- database_setup.py              # MySQL schema setup script
|-- email_utils.py                 # Email helper functions
|-- mail_config.py                 # Local SMTP configuration
|-- requirements.txt               # Python dependencies
|-- templates/                     # Flask HTML templates
|-- static/                        # CSS and JavaScript assets
|-- dataset/                       # Face image dataset
|-- encode_faces.py                # Face encoding helper
|-- recognize.py                   # Recognition helper script
`-- train_model.py                 # Training helper script
```

## Prerequisites

- Python 3.10+ recommended
- MySQL Server
- A working webcam/camera for face registration and attendance
- Windows users may use the included `dlib-19.24.2-cp312-cp312-win_amd64.whl` if installing `dlib` from source fails

## Setup

1. Create and activate a virtual environment.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

If `dlib` or `face-recognition` installation fails on Windows, install the included wheel first:

```powershell
pip install .\dlib-19.24.2-cp312-cp312-win_amd64.whl
pip install -r requirements.txt
```

3. Configure MySQL.

The current local database defaults are:

```text
host: localhost
user: root
password: root123
database: attendance_system
```

You can override these values with environment variables:

```powershell
$env:DB_HOST = 'localhost'
$env:DB_USER = 'root'
$env:DB_PASSWORD = 'root123'
$env:DB_NAME = 'attendance_system'
```

The app reads `DB_HOST`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` from the environment, with the above defaults if they are not set.

Update your MySQL credentials in environment variables rather than editing `database.py` or `database_setup.py` directly.

4. Create the database schema.

```powershell
python database_setup.py
```

5. Optional: configure email.

Update `mail_config.py` with your SMTP account details if you want registration emails to be sent. For Gmail, use an app password instead of your normal account password. Also make sure `MAIL_USE_TLS = True` and `MAIL_PORT = 587` when using Gmail SMTP.

## Run the App

```powershell
python app.py
```

Open the app in your browser:

```text
http://localhost:8080
```

### Optional: Run with HTTPS for browser camera access

If you need secure local access for the camera, enable HTTPS with a self-signed certificate:

```powershell
$env:USE_HTTPS = 'true'
python app.py
```

Then open either:

```text
https://localhost:8080
https://127.0.0.1:8080
```

Accept the browser warning for the self-signed certificate.

The Flask app runs on `0.0.0.0:8080` by default.

## Common Workflows

1. Start MySQL.
2. Run `python app.py`.
3. Log in through the admin page.
4. Register students with their details and face image.
5. Mark attendance through face recognition, classroom photo upload, or voice check-in.
6. Review attendance from the dashboard.
7. Export daily, monthly, or complete reports as CSV/Excel.

## Reports

FRAS supports:

- Daily attendance reports by program, year, section, and date
- Monthly attendance percentage reports
- Complete attendance exports
- Excel exports with formatted headers, status colors, and timestamps
- CSV exports for spreadsheet and data-analysis tools

See `QUICK_START_GUIDE.md` and `REPORT_GENERATION_FEATURES.md` for more details about report workflows.

## Notes

- Keep local credentials out of public commits.
- `encodings.pickle`, `dataset/`, and database records are runtime data and may need to be regenerated or backed up depending on your environment.
- If camera access fails, check browser permissions and confirm that no other application is using the camera.
