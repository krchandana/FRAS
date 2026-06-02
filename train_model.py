import face_recognition
import dlib
import os
import pickle

dataset_path = "dataset"

known_encodings = []
known_ids = []

print("Processing images...")

# NOTE: It is assumed that the image files in the 'dataset' folder are named
# with the student ID (e.g., 'ST101.jpg', 'ST102.png').
# Initialize dlib's face detector
detector = dlib.get_frontal_face_detector()

for file in os.listdir(dataset_path):

    image_path = os.path.join(dataset_path, file)

    image = face_recognition.load_image_file(image_path)

    # Detect face locations using dlib
    face_locations = detector(image, 1)
    encodings = face_recognition.face_encodings(image, face_locations)

    if len(encodings) > 0:

        encoding = encodings[0]

        student_id = os.path.splitext(file)[0]

        known_encodings.append(encoding)
        known_ids.append(student_id)

print("Saving encodings...")

data = {
    "encodings": known_encodings,
    "ids": known_ids
}

with open("encodings.pickle", "wb") as f:
    pickle.dump(data, f)

print("Training complete. encodings.pickle created.")