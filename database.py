import mysql.connector
from datetime import datetime
from mysql.connector import Error
import face_recognition
import cv2
import numpy as np
import os
import base64
from io import BytesIO
from PIL import Image, ImageOps

# MySQL connection
def connect_db():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root123",
        database="attendance_system"
    )
    return db


def ensure_attendance_metadata_columns():
    """Ensure attendance table has subject and period metadata columns."""
    try:
        db = connect_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'attendance'
              AND column_name IN ('subject_name', 'period_duration')
        """)
        existing_cols = {row[0] for row in cursor.fetchall()}

        if 'subject_name' not in existing_cols:
            cursor.execute("ALTER TABLE attendance ADD COLUMN subject_name VARCHAR(100) NULL")
        if 'period_duration' not in existing_cols:
            cursor.execute("ALTER TABLE attendance ADD COLUMN period_duration VARCHAR(50) NULL")

        cursor.execute("""
            SELECT column_name
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = 'attendance'
              AND index_name = 'unique_attendance'
            ORDER BY seq_in_index
        """)
        unique_cols = [row[0] for row in cursor.fetchall()]
        if unique_cols and unique_cols != ['student_id', 'date', 'time']:
            cursor.execute("ALTER TABLE attendance DROP INDEX unique_attendance")
            unique_cols = []
        if not unique_cols:
            cursor.execute(
                "ALTER TABLE attendance ADD UNIQUE KEY unique_attendance (student_id, date, time)"
            )

        db.commit()
        cursor.close()
        db.close()
    except Error as e:
        print(f"Error ensuring attendance metadata columns: {e}")


def ensure_student_voice_column():
    """Ensure students table has a voice passphrase column."""
    try:
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'students'
              AND column_name = 'voice_passphrase'
        """)
        exists = cursor.fetchone()
        if not exists:
            cursor.execute("ALTER TABLE students ADD COLUMN voice_passphrase VARCHAR(150) NULL")
            db.commit()
        cursor.close()
        db.close()
    except Error as e:
        print(f"Error ensuring student voice column: {e}")


# Insert new student with program, year, and section
def add_student(student_id, name, program, year, section, email=None, phone=None, face_image=None, face_encoding=None, voice_passphrase=None):
    """
    Add a new student to the database
    
    Parameters:
    - student_id: Unique student identifier
    - name: Student's full name
    - program: 'MCA' or 'BCA'
    - year: 1 or 2 (for MCA), 1, 2, or 3 (for BCA)
    - section: 'A' or 'B'
    - email: Student's email (optional)
    - phone: Student's phone number (optional)
    - face_image: Student's face image (optional, binary)
    - face_encoding: Face encoding for recognition (optional, binary)
    """
    try:
        ensure_student_voice_column()
        db = connect_db()
        cursor = db.cursor()

        query = """
            INSERT INTO students (id, name, program, year, section, email, phone, face_image, face_encoding, voice_passphrase)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (student_id, name, program.upper(), year, section.upper(), email, phone, face_image, face_encoding, voice_passphrase)

        cursor.execute(query, values)
        db.commit()
        
        cursor.close()
        db.close()
        return True
        
    except Error as e:
        print(f"Error adding student: {e}")
        return False


# Delete student
def delete_student(student_id):
    """Delete a student and their attendance records"""
    try:
        db = connect_db()
        cursor = db.cursor()

        # Delete from attendance tables first due to foreign keys
        cursor.execute("DELETE FROM attendance WHERE student_id = %s", (student_id,))
        cursor.execute("DELETE FROM attendance_summary WHERE student_id = %s", (student_id,))
        
        # Delete from students table
        cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
        
        db.commit()
        cursor.close()
        db.close()
        return True
    except Error as e:
        print(f"Error deleting student: {e}")
        return False


# Get all students
def get_students():
    try:
        db = connect_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM students ORDER BY program, year, section, name")
        data = cursor.fetchall()

        cursor.close()
        db.close()

        return data
    except Error as e:
        print(f"Error fetching students: {e}")
        return []


# Get students by program and year
def get_students_by_program_year(program, year):
    """Get all students for a specific program and year"""
    try:
        db = connect_db()
        cursor = db.cursor()

        query = "SELECT * FROM students WHERE program = %s AND year = %s ORDER BY section, name"
        cursor.execute(query, (program.upper(), year))
        data = cursor.fetchall()

        cursor.close()
        db.close()

        return data
    except Error as e:
        print(f"Error fetching students: {e}")
        return []


# Get students by section
def get_students_by_section(program, year, section):
    """Get all students in a specific section"""
    try:
        db = connect_db()
        cursor = db.cursor()

        query = "SELECT * FROM students WHERE program = %s AND year = %s AND section = %s ORDER BY name"
        cursor.execute(query, (program.upper(), year, section.upper()))
        data = cursor.fetchall()

        cursor.close()
        db.close()

        return data
    except Error as e:
        print(f"Error fetching students: {e}")
        return []


def get_student_by_id(student_id):
    """Get a single student by ID."""
    try:
        db = connect_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
        data = cursor.fetchone()

        cursor.close()
        db.close()
        return data
    except Error as e:
        print(f"Error fetching student by id: {e}")
        return None


def get_student_notification_data(student_id):
    """Get minimal student data needed for email notifications."""
    try:
        db = connect_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, name, program, year, section, email FROM students WHERE id = %s",
            (student_id,)
        )
        data = cursor.fetchone()
        cursor.close()
        db.close()
        return data
    except Error as e:
        print(f"Error fetching student notification data: {e}")
        return None


def get_students_notification_data(student_ids):
    """Get student notification data for multiple student ids."""
    if not student_ids:
        return []

    try:
        db = connect_db()
        cursor = db.cursor()
        placeholders = ','.join(['%s'] * len(student_ids))
        query = f"""
            SELECT id, name, program, year, section, email
            FROM students
            WHERE id IN ({placeholders})
        """
        cursor.execute(query, tuple(student_ids))
        data = cursor.fetchall()
        cursor.close()
        db.close()
        return data
    except Error as e:
        print(f"Error fetching student notification data list: {e}")
        return []


def get_student_voice_data(student_id):
    """Get minimal student data required for voice check-in."""
    try:
        ensure_student_voice_column()
        db = connect_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, name, voice_passphrase, program, year, section FROM students WHERE id = %s",
            (student_id,)
        )
        data = cursor.fetchone()
        cursor.close()
        db.close()
        return data
    except Error as e:
        print(f"Error fetching student voice data: {e}")
        return None


def update_student(student_id, name, program, year, section, email=None, phone=None):
    """Update editable student details."""
    try:
        db = connect_db()
        cursor = db.cursor()

        query = """
            UPDATE students
            SET name = %s, program = %s, year = %s, section = %s, email = %s, phone = %s
            WHERE id = %s
        """
        values = (name, program.upper(), year, section.upper(), email, phone, student_id)
        cursor.execute(query, values)
        db.commit()

        cursor.close()
        db.close()
        return True
    except Error as e:
        print(f"Error updating student: {e}")
        return False


# Mark attendance
def mark_attendance(student_id, status="Present", date=None, time=None, subject_name=None, period_duration=None):
    """Mark attendance for a student"""
    try:
        ensure_attendance_metadata_columns()
        db = connect_db()
        cursor = db.cursor()

        now = datetime.now()
        if date is None:
            date = now.strftime("%Y-%m-%d")
        if time is None:
            time = now.strftime("%H:%M:%S")

        query = """
            INSERT INTO attendance (student_id, date, time, status, subject_name, period_duration)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status=%s,
                time=%s,
                subject_name=%s,
                period_duration=%s
        """
        values = (
            student_id, date, time, status, subject_name, period_duration,
            status, time, subject_name, period_duration
        )

        cursor.execute(query, values)
        db.commit()

        cursor.close()
        db.close()
        return True
        
    except Error as e:
        print(f"Error marking attendance: {e}")
        return False


# Mark multiple students' attendance
def mark_section_attendance(section_students, status="Present", date=None, time=None, subject_name=None, period_duration=None):
    """Mark attendance for multiple students"""
    try:
        ensure_attendance_metadata_columns()
        db = connect_db()
        cursor = db.cursor()

        now = datetime.now()
        if date is None:
            date = now.strftime("%Y-%m-%d")
        if time is None:
            time = now.strftime("%H:%M:%S")

        for student_id in section_students:
            query = """
                INSERT INTO attendance (student_id, date, time, status, subject_name, period_duration)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    status=%s,
                    time=%s,
                    subject_name=%s,
                    period_duration=%s
            """
            values = (
                student_id, date, time, status, subject_name, period_duration,
                status, time, subject_name, period_duration
            )
            cursor.execute(query, values)

        db.commit()
        cursor.close()
        db.close()
        return True
        
    except Error as e:
        print(f"Error marking attendance: {e}")
        return False


# Get attendance report
def get_attendance():
    """Get all attendance records"""
    try:
        db = connect_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT a.*, s.name, s.program, s.year, s.section 
            FROM attendance a 
            JOIN students s ON a.student_id = s.id 
            ORDER BY a.date DESC, s.program, s.year, s.section
        """)
        data = cursor.fetchall()

        cursor.close()
        db.close()

        return data
    except Error as e:
        print(f"Error fetching attendance: {e}")
        return []


# Get attendance for specific date and section
def get_attendance_by_section(program, year, section, date=None):
    """Get attendance records for a specific section and date"""
    try:
        db = connect_db()
        cursor = db.cursor()

        if date:
            query = """
                SELECT a.*, s.name 
                FROM attendance a 
                JOIN students s ON a.student_id = s.id 
                WHERE s.program = %s AND s.year = %s AND s.section = %s AND a.date = %s
                ORDER BY s.name
            """
            cursor.execute(query, (program.upper(), year, section.upper(), date))
        else:
            query = """
                SELECT a.*, s.name 
                FROM attendance a 
                JOIN students s ON a.student_id = s.id 
                WHERE s.program = %s AND s.year = %s AND s.section = %s
                ORDER BY a.date DESC, s.name
            """
            cursor.execute(query, (program.upper(), year, section.upper()))

        data = cursor.fetchall()
        cursor.close()
        db.close()

        return data
    except Error as e:
        print(f"Error fetching attendance: {e}")
        return []


def get_attendance_by_program_year(program, year):
    """Get attendance records for a program and year across all sections."""
    try:
        ensure_attendance_metadata_columns()
        db = connect_db()
        cursor = db.cursor()

        query = """
            SELECT
                a.attendance_id,
                a.student_id,
                a.date,
                a.time,
                a.status,
                a.subject_name,
                a.period_duration,
                s.name,
                s.program,
                s.year,
                s.section
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE s.program = %s AND s.year = %s
            ORDER BY a.date DESC, a.time DESC, s.section, s.name
        """
        cursor.execute(query, (program.upper(), year))
        data = cursor.fetchall()

        cursor.close()
        db.close()
        return data
    except Error as e:
        print(f"Error fetching attendance by program/year: {e}")
        return []


def get_attendance_sheet(program, year, section, date, time, subject_name=None, period_duration=None):
    """Get one attendance sheet for a class, date, time, subject, and period."""
    try:
        ensure_attendance_metadata_columns()
        db = connect_db()
        cursor = db.cursor()

        base_query = """
            SELECT
                a.attendance_id,
                a.student_id,
                a.date,
                a.time,
                a.status,
                a.subject_name,
                a.period_duration,
                s.name,
                s.program,
                s.year,
                s.section
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE s.program = %s
              AND s.year = %s
              AND s.section = %s
              AND a.date = %s
        """
        params = [program.upper(), year, section.upper(), date]
        time_value = str(time)[:5] if time else ''

        if time_value:
            base_query += " AND TIME_FORMAT(a.time, '%H:%i') = %s"
            params.append(time_value)

        query = base_query
        query_params = list(params)
        if subject_name is not None:
            query += " AND COALESCE(a.subject_name, '') = %s"
            query_params.append(subject_name or '')
        if period_duration is not None:
            query += " AND COALESCE(a.period_duration, '') = %s"
            query_params.append(period_duration or '')
        query += " ORDER BY s.name"

        cursor.execute(query, tuple(query_params))
        data = cursor.fetchall()

        if not data and (subject_name is not None or period_duration is not None):
            cursor.execute(base_query + " ORDER BY s.name", tuple(params))
            data = cursor.fetchall()

        cursor.close()
        db.close()
        return data
    except Error as e:
        print(f"Error fetching attendance sheet: {e}")
        return []


def delete_attendance_sheet(program, year, section, date, time, subject_name=None, period_duration=None):
    """Delete an attendance sheet by program/year/section/date/time."""
    try:
        ensure_attendance_metadata_columns()
        db = connect_db()
        cursor = db.cursor()

        query = """
            DELETE a
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE s.program = %s
              AND s.year = %s
              AND s.section = %s
              AND a.date = %s
              AND a.time = %s
              AND COALESCE(a.subject_name, '') = %s
              AND COALESCE(a.period_duration, '') = %s
        """
        cursor.execute(
            query,
            (
                program.upper(), year, section.upper(), date, time,
                (subject_name or ''), (period_duration or '')
            )
        )
        db.commit()

        deleted_rows = cursor.rowcount
        cursor.close()
        db.close()
        return deleted_rows >= 0
    except Error as e:
        print(f"Error deleting attendance sheet: {e}")
        return False


# Get attendace summary for a student
def get_student_attendance_summary(student_id, month=None, year=None):
    """Get attendance summary for a student"""
    try:
        db = connect_db()
        cursor = db.cursor()

        if month and year:
            query = """
                SELECT * FROM attendance 
                WHERE student_id = %s AND MONTH(date) = %s AND YEAR(date) = %s
            """
            cursor.execute(query, (student_id, month, year))
        else:
            query = "SELECT * FROM attendance WHERE student_id = %s"
            cursor.execute(query, (student_id,))

        data = cursor.fetchall()
        cursor.close()
        db.close()

        return data
    except Error as e:
        print(f"Error fetching attendance summary: {e}")
        return []


# Process classroom photo and mark attendance automatically
def process_classroom_photo(classroom_image_data, program, year, section, date=None, time=None, subject_name=None, period_duration=None):
    """
    Process a classroom photo and mark attendance based on face recognition
    
    Parameters:
    - classroom_image_data: Base64 encoded classroom photo
    - program: 'MCA' or 'BCA'
    - year: Year number
    - section: 'A' or 'B'
    - date: Date for attendance (optional, defaults to today)
    - time: Time for attendance (optional, defaults to current time)
    
    Returns:
    - Dictionary with attendance results
    """
    try:
        # Get all students in the class
        students = get_students_by_section(program, year, section)
        if not students:
            return {'error': 'No students found in this class'}
        
        # Get face encodings for registered students
        known_face_encodings = []
        known_face_ids = []
        
        for student in students:
            if student[8]:  # face_encoding column
                try:
                    encoding = np.frombuffer(student[8], dtype=np.float64)
                    if encoding.shape[0] != 128:
                        continue
                    known_face_encodings.append(encoding)
                    known_face_ids.append(student[0])  # student_id
                except Exception:
                    continue
        
        if not known_face_encodings:
            return {'error': f'Found {len(students)} students in this class, but none have valid face data registered. Please delete and re-register these students with clear photos.'}
        
        # Decode classroom image
        try:
            if ',' in classroom_image_data:
                image_data = base64.b64decode(classroom_image_data.split(',')[1])
            else:
                image_data = base64.b64decode(classroom_image_data)
        except Exception as e:
            return {'error': 'Invalid image data format'}

        try:
            classroom_image = Image.open(BytesIO(image_data))
            classroom_image = ImageOps.exif_transpose(classroom_image).convert("RGB")
        except Exception:
            return {'error': 'Could not read the uploaded image. Please use a JPG, PNG, or WEBP photo.'}

        max_dimension = 1800
        if max(classroom_image.size) > max_dimension:
            resample_filter = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)
            classroom_image.thumbnail((max_dimension, max_dimension), resample_filter)

        classroom_np = np.asarray(classroom_image, dtype=np.uint8)

        # The face_recognition library expects an 8-bit RGB image. Phone photos
        # often include EXIF rotation or alpha channels, so normalize first.
        # Find faces in classroom photo
        # face_locations = face_recognition.face_locations(classroom_np)
        # face_encodings = face_recognition.face_encodings(classroom_np, face_locations)
        
        # Improve detection: Upsample 2x to find smaller faces (students in back rows)
        upsample_count = 2 if max(classroom_image.size) <= 1400 else 1
        face_locations = face_recognition.face_locations(classroom_np, number_of_times_to_upsample=upsample_count)
        face_encodings = face_recognition.face_encodings(classroom_np, face_locations)
        
        if not face_encodings:
            return {'error': 'No faces detected in the classroom photo'}
        
        # Match faces with known students
        present_students = []
        absent_students = []
        
        # Initialize all students as absent first (including those without face data)
        for s in students:
            absent_students.append(s[0]) # s[0] is student_id
        
        for face_encoding in face_encodings:
            # Improve matching: Lower tolerance to 0.5 (default 0.6) to reduce false positives
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.5)
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            
            if True in matches:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    matched_student_id = known_face_ids[best_match_index]
                    if matched_student_id in absent_students:
                        absent_students.remove(matched_student_id)
                        present_students.append(matched_student_id)
        
        # Mark attendance in database
        attendance_results = []
        
        # Optimize DB updates: Use batch processing instead of opening a connection per student
        if present_students:
            mark_section_attendance(present_students, "Present", date, time, subject_name, period_duration)
            for student_id in present_students:
                attendance_results.append({'student_id': student_id, 'status': 'Present'})
            
        if absent_students:
            mark_section_attendance(absent_students, "Absent", date, time, subject_name, period_duration)
            for student_id in absent_students:
                attendance_results.append({'student_id': student_id, 'status': 'Absent'})

        return {
            'success': True,
            'total_faces_detected': len(face_encodings),
            'present_count': len(present_students),
            'absent_count': len(absent_students),
            'attendance': attendance_results,
            'present_students': present_students,
            'absent_students': absent_students
        }
        
    except Exception as e:
        print(f"Error processing classroom photo: {e}")
        return {'error': str(e)}


# Get student face image
def get_student_face_image(student_id):
    """Get student's face image for display"""
    try:
        db = connect_db()
        cursor = db.cursor()

        cursor.execute("SELECT face_image FROM students WHERE id = %s", (student_id,))
        result = cursor.fetchone()

        cursor.close()
        db.close()

        if result and result[0]:
            return base64.b64encode(result[0]).decode('utf-8')
        return None
        
    except Error as e:
        print(f"Error fetching face image: {e}")
        return None


# Get student statistics by program/year/section
def get_student_statistics():
    """Get count of students grouped by program, year, and section"""
    try:
        db = connect_db()
        cursor = db.cursor()

        query = """
            SELECT program, year, section, COUNT(*) as count
            FROM students
            GROUP BY program, year, section
            ORDER BY program, year, section
        """
        cursor.execute(query)
        data = cursor.fetchall()

        cursor.close()
        db.close()

        return data
    except Error as e:
        print(f"Error fetching student statistics: {e}")
        return []


def get_daily_attendance(program, year, section, date):
    """Get attendance summary for a specific day for a section"""
    try:
        db = connect_db()
        cursor = db.cursor()

        query = """
            SELECT
                s.id,
                s.name,
                a.status,
                a.date,
                a.time,
                a.subject_name,
                a.period_duration
            FROM students s
            LEFT JOIN attendance a ON s.id = a.student_id AND a.date = %s
            WHERE s.program = %s AND s.year = %s AND s.section = %s
            ORDER BY s.name
        """
        cursor.execute(query, (date, program.upper(), year, section.upper()))
        data = cursor.fetchall()

        cursor.close()
        db.close()

        return data
    except Error as e:
        print(f"Error fetching daily attendance: {e}")
        return []


def get_monthly_attendance_percentage(program, year, month, year_val):
    """Get monthly attendance percentage for all students in a class"""
    try:
        db = connect_db()
        cursor = db.cursor()

        query = """
            SELECT
                s.id,
                s.name,
                s.section,
                COUNT(CASE WHEN a.status = 'Present' THEN 1 END) as present_days,
                COUNT(DISTINCT a.date) as attendance_days,
                ROUND(
                    COUNT(CASE WHEN a.status = 'Present' THEN 1 END) * 100.0 /
                    NULLIF(COUNT(DISTINCT a.date), 0), 2
                ) as percentage
            FROM students s
            LEFT JOIN attendance a ON s.id = a.student_id
                AND MONTH(a.date) = %s
                AND YEAR(a.date) = %s
                AND a.status IN ('Present', 'Absent')
            WHERE s.program = %s AND s.year = %s
            GROUP BY s.id, s.name, s.section
            ORDER BY s.section, s.name
        """
        cursor.execute(query, (month, year_val, program.upper(), year))
        data = cursor.fetchall()

        cursor.close()
        db.close()

        return data
    except Error as e:
        print(f"Error fetching monthly attendance percentage: {e}")
        return []


def get_attendance_summary_range(program, year, section, start_date, end_date):
    """Get attendance summary for a date range"""
    try:
        db = connect_db()
        cursor = db.cursor()

        query = """
            SELECT
                s.id,
                s.name,
                s.section,
                COUNT(CASE WHEN a.status = 'Present' THEN 1 END) as present_count,
                COUNT(CASE WHEN a.status = 'Absent' THEN 1 END) as absent_count,
                COUNT(DISTINCT a.date) as total_days
            FROM students s
            LEFT JOIN attendance a ON s.id = a.student_id
                AND a.date BETWEEN %s AND %s
            WHERE s.program = %s AND s.year = %s AND s.section = %s
            GROUP BY s.id, s.name, s.section
            ORDER BY s.name
        """
        cursor.execute(query, (start_date, end_date, program.upper(), year, section.upper()))
        data = cursor.fetchall()

        cursor.close()
        db.close()

        return data
    except Error as e:
        print(f"Error fetching attendance summary range: {e}")
        return []


def get_all_attendance_for_export(program=None, year=None, section=None, start_date=None, end_date=None):
    """Get all attendance records for export, with optional filters"""
    try:
        db = connect_db()
        cursor = db.cursor()

        query = """
            SELECT
                s.id as student_id,
                s.name,
                s.program,
                s.year,
                s.section,
                a.date,
                a.time,
                a.status,
                a.subject_name,
                a.period_duration
            FROM students s
            JOIN attendance a ON s.id = a.student_id
            WHERE 1=1
        """
        params = []

        if program:
            query += " AND s.program = %s"
            params.append(program.upper())
        if year:
            query += " AND s.year = %s"
            params.append(year)
        if section:
            query += " AND s.section = %s"
            params.append(section.upper())
        if start_date:
            query += " AND a.date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND a.date <= %s"
            params.append(end_date)

        query += " ORDER BY a.date DESC, s.program, s.year, s.section, s.name"

        cursor.execute(query, params)
        data = cursor.fetchall()

        cursor.close()
        db.close()

        return data
    except Error as e:
        print(f"Error fetching attendance for export: {e}")
        return []


def get_student_monthly_attendance(student_id, month, year_val):
    """Get attendance records for a student for a specific month"""
    try:
        db = connect_db()
        cursor = db.cursor()

        query = """
            SELECT
                a.date,
                a.time,
                a.status,
                a.subject_name,
                a.period_duration
            FROM attendance a
            WHERE a.student_id = %s
                AND MONTH(a.date) = %s
                AND YEAR(a.date) = %s
            ORDER BY a.date, a.time
        """
        cursor.execute(query, (student_id, month, year_val))
        data = cursor.fetchall()

        cursor.close()
        db.close()

        return data
    except Error as e:
        print(f"Error fetching student monthly attendance: {e}")
        return []
