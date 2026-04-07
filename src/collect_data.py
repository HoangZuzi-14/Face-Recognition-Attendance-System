import cv2
import os

def collect_faces(person_name, num_images=50, save_dir="data/raw"):
    person_dir = os.path.join(save_dir, person_name)
    os.makedirs(person_dir, exist_ok=True)

    cap = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    count = 0
    print(f"Collecting images for: {person_name}")
    print("Press SPACE to capture, Q to quit.")

    while count < num_images:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Flip horizontally for a mirror effect
        frame = cv2.flip(frame, 1)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Lower scaleFactor (e.g. 1.1) and minNeighbors (e.g. 4) makes detection more sensitive,
        # which helps significantly with glasses or minor lighting changes.
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        cv2.putText(frame, f"Captured: {count}/{num_images}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, "SPACE=capture  Q=quit",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        cv2.imshow("Collect Data", frame)

        key = cv2.waitKey(1)
        if key == ord(' ') and len(faces) > 0:
            img_path = os.path.join(person_dir, f"{person_name}_{count:03d}.jpg")
            cv2.imwrite(img_path, frame)
            count += 1
            print(f"  [{count}/{num_images}] Saved: {img_path}")
        elif key == ord(' ') and len(faces) == 0:
            print("  No face detected, try again!")
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nDone! Saved {count} images to {person_dir}")

if __name__ == "__main__":
    name = input("Enter person name (no spaces, e.g. Hoang_Vu): ").strip()
    if name:
        collect_faces(name)
    else:
        print("Invalid name!")