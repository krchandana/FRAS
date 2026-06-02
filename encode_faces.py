import face_recognition
import os
import pickle

# Path to your student images
dataset_path = "dataset/MCA/1A"  # Update if your folder is different

# File where encodings will be saved
encoding_file = "encodings.pickle"

known_encodings = []
known_names = []

# Loop through each image in the dataset folder
for file in os.listdir(dataset_path):
    if file.endswith((".jpg", ".jpeg", ".png")):
        path = os.path.join(dataset_path, file)
        image = face_recognition.load_image_file(path)
        encodings = face_recognition.face_encodings(image)
        if encodings:
            known_encodings.append(encodings[0])
            known_names.append(os.path.splitext(file)[0])

# Save encodings to a pickle file
data = {"encodings": known_encodings, "names": known_names}

with open(encoding_file, "wb") as f:
    pickle.dump(data, f)

print("Encodings generated for", len(known_names), "students.")