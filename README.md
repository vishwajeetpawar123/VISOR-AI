# 👁️ Visor AI: The "Living" Attendance System

> **"Transforming passive CCTV into an active, intelligent campus assistant."**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-green.svg)](https://opencv.org/)
[![Flask](https://img.shields.io/badge/Flask-Web%20Server-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Ollama](https://img.shields.io/badge/AI-Ollama%20Local-orange.svg)](https://ollama.ai/)

---

## 🚀 The Proposal

**Smart Campus Challenge:** Traditional attendance systems are slow, manual, and prone to "proxy" cheating. Security cameras record passively but provide no real-time intelligence.

**Our Solution:** **Visor AI** is a dual-mode system (Surveillance + Attendance) that uses existing camera infrastructure to:

1. **Automate Attendance:** Recognize students seamlessly as they walk in.
2. **Ensure Security:** Monitor for unauthorized access in real-time.
3. **Provide Insights:** An integrated **Local LLM Assistant** that allows teachers to *chat* with their attendance logs (e.g., "Who was late today?").

---

## ✨ Key Features

* **🧐 Real-Time Face Recognition:** Sub-second identification using dlib & OpenCV.
* **🧠 Local AI Interaction:** Built-in Chatbox powered by **Ollama (Qwen 2.5)**. No data leaves the campus.
* **🛡️ Dual Modes:**
  * **Surveillance Mode:** Logs all entries/exits for security.
  * **Attendance Mode:** optimized for classrooms (preventing duplicate logs).
* **🎨 Premium UI:** Glassmorphism design inspired by Stripe, making enterprise tools feel modern.
* **📊 Smart Logging:** Tracks Entry Time, Exit Time, and Duration automatically.

---

## 🧠 How it Works 

### The Logic Gate (3-Second Rule)

Visor AI distinguishes between a casual glance and a confirmed attendance.

1. **Entry:** When a known face is detected, they are marked as "Present" and their timestamp is logged.
2. **Monitoring:** The system tracks them as long as they are in frame.
3. **Exit:** If the face is lost for more than **3 Seconds**, an "EXIT" event is logged and the duration is calculated.

### Performance Optimization

* **0.25x Resizing:** We downscale the video feed to 1/4th resolution for the face detection pipeline, significantly reducing CPU load.
* **Frame Skipping:** The heavy Face Recognition (ResNet) model only runs on every **5th frame**, balancing real-time speed with high accuracy.

## 🛡️ Privacy Architecture

Visor AI is designed to be **Air-Gapped**.

* **Local Embeddings:** Face data is converted to 128-d vectors and stored in a local `.pkl` file. No images are sent to the cloud.
* **Local LLM:** The AI Assistant allows natural language queries by running **Ollama** locally, ensuring student data never leaves the campus server.

---

## 🛠️ Tech Stack

* **Core:** Python 3.12
* **Vision:** OpenCV, Face_Recognition (dlib)
* **Web Framework:** Flask (Lightweight/Fast)
* **Generative AI:** Ollama (Local Large Language Model)
* **Database:** CSV (Rapid Prototyping) / Easy migration to SQL.
* **Frontend:** HTML5, CSS3 (Vanilla), JavaScript.

---

## 📸 Screenshots

*(Placeholders for Hackathon Submission)*

| Live Feed & Dashboard | AI Chat Assistant |
| :---: | :---: |
| *Real-time recognition with bounding boxes.* | *Asking the AI "Who is absent?"* |

---

## ⚙️ Installation & Setup

1. **Clone the Repository**

    ```bash
    git clone https://github.com/yourusername/visor-ai.git
    cd visor-ai
    ```

2. **Create & Activate Virtual Environment**
    * It is recommended to use a virtual environment named `.venv_new` to match the project scripts.

    **Windows:**

    ```bash
    python -m venv .venv_new
    .\.venv_new\Scripts\activate
    ```

    **Linux/Mac:**

    ```bash
    python3 -m venv .venv_new
    source .venv_new/bin/activate
    ```

3. **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

    *(Note: Ensures you have CMake installed for dlib)*

4. **Setup Faces**
    * Place photo of students in the `/faces` directory.
    * Name them `Firstname_Lastname.jpg`.

5. **Run the System**

    ```bash
    python final_attendance_app.py
    ```

6. **Access Dashboard**
    * Open Browser: `http://127.0.0.1:5000`

---

## 🔮 Future Roadmap

* **Teacher's Transcompiler:** Voice-activated macros (e.g., "Mark everyone present except John").
* **Mobile App:** Integration for push notifications on unauthorized entry.
* **Emotion Analysis:** Gauging student engagement during lectures.

---

## 📚 Technical Documentation

For a deep dive into the system architecture, memory management, and logic flows, please refer to the [Technical Reference Manual](TECHNICAL_REFERENCE.md).

---

*Built with ❤️ for the Smart Campus Hackathon.*
