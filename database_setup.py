import mysql.connector
from mysql.connector import Error

def setup_database():
    """Setup the database schema for attendance system"""
    try:
        # Connect to MySQL server
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root123"
        )
        
        cursor = connection.cursor()
        
        # Create database if not exists
        cursor.execute("CREATE DATABASE IF NOT EXISTS attendance_system")
        print("Database created successfully")
        
        # Connect to the attendance_system database
        connection.close()
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root123",
            database="attendance_system"
        )
        
        cursor = connection.cursor()
        
        # Drop existing tables if they exist (for fresh setup) - drop in correct order for foreign keys
        cursor.execute("DROP TABLE IF EXISTS attendance_summary")
        cursor.execute("DROP TABLE IF EXISTS attendance")
        cursor.execute("DROP TABLE IF EXISTS students")
        
        # Create students table with program, year, and section
        students_table = """
        CREATE TABLE students (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            program VARCHAR(10) NOT NULL,
            year INT NOT NULL,
            section VARCHAR(5) NOT NULL,
            email VARCHAR(100),
            phone VARCHAR(10),
            face_image LONGBLOB,
            face_encoding LONGBLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            voice_passphrase VARCHAR(150)
        )
        """
        cursor.execute(students_table)
        print("Students table created successfully")
        
        # Create attendance table
        attendance_table = """
        CREATE TABLE attendance (
            attendance_id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL,
            status VARCHAR(20) DEFAULT 'Present',
            subject_name VARCHAR(100),
            period_duration VARCHAR(50),
            FOREIGN KEY (student_id) REFERENCES students(id),
            UNIQUE KEY unique_attendance (student_id, date, time)
        )
        """
        cursor.execute(attendance_table)
        print("Attendance table created successfully")
        
        # Create a summary table for attendance statistics
        summary_table = """
        CREATE TABLE attendance_summary (
            summary_id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(50) NOT NULL,
            month INT NOT NULL,
            year INT NOT NULL,
            total_days INT DEFAULT 0,
            present_days INT DEFAULT 0,
            absent_days INT DEFAULT 0,
            FOREIGN KEY (student_id) REFERENCES students(id),
            UNIQUE KEY unique_summary (student_id, month, year)
        )
        """
        cursor.execute(summary_table)
        print("Attendance summary table created successfully")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("\nDatabase setup completed successfully!")
        
    except Error as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    setup_database()
