import cv2
import face_recognition
import pickle
import numpy as np
from database import mark_attendance

# Load trained encodings
print("Loading trained model...")

with open("encodings.pickle", "rb") as f:
    data = pickle.load(f)

# Start webcam
video = cv2.VideoCapture(0)

print("Starting Face Recognition...")

marked_ids = []

while True:
    
    ret, frame = video.read()

    if not ret:
        break

    # Convert image to RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detect faces
    boxes = face_recognition.face_locations(rgb)

    # Encode faces
    encodings = face_recognition.face_encodings(rgb, boxes)

    ids = []

    for encoding in encodings:

        # Compare face with known faces
        matches = face_recognition.compare_faces(data["encodings"], encoding, tolerance=0.6)
        student_id = "Unknown"

        if True in matches:
            # Find the best match
            face_distances = face_recognition.face_distance(data["encodings"], encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                student_id = data["ids"][best_match_index]

                # Mark attendance only once per session
                if student_id not in marked_ids:
                    if mark_attendance(student_id):
                        print(f"Attendance marked for {student_id}")
                        marked_ids.append(student_id)

        ids.append(student_id)

    # Draw boxes around faces
    for ((top, right, bottom, left), student_id) in zip(boxes, ids):

        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        cv2.putText(frame, student_id, (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (0, 255, 0), 2)

    cv2.imshow("Face Recognition Attendance", frame)

    # Press ESC to exit
    if cv2.waitKey(1) == 27:
        break


video.release()
cv2.destroyAllWindows()

print("Attendance completed.")