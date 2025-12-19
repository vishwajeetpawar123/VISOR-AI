import os
from flask import Flask, render_template, send_from_directory, jsonify
from datetime import datetime

app = Flask(__name__)

# Configuration
PHOTOS_DIR = os.path.join(os.getcwd(), 'attendance_photos')
app.config['PHOTOS_FOLDER'] = PHOTOS_DIR

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/photos')
def get_photos():
    """Returns a list of photo metadata (JSON) for the frontend to render."""
    if not os.path.exists(PHOTOS_DIR):
        return jsonify([])

    files = [f for f in os.listdir(PHOTOS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(PHOTOS_DIR, x)), reverse=True)
    
    photo_data = []
    for filename in files:
        # Expected format: Attendance_Name_YYYYMMDD_HHMMSS.jpg
        # But we should be robust.
        parts = filename.split('_')
        display_name = "Unknown"
        timestamp_str = "Unknown"
        
        if len(parts) >= 3:
            # Try to parse Name and Timestamp
            # Name might contain underscores? In our main script, we sanitized it.
            # safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '_')]).strip()
            # Timestamp is the last part: YYYYMMDD_HHMMSS.jpg -> we need to split extension.
            
            # Let's rely on file mtime for robust sorting/display, 
            # but try to extract name for display.
            
            # parts[0] is "Attendance"
            # parts[-2] is "YYYYMMDD" (part of timestamp)
            # parts[-1] is "HHMMSS.jpg"
            
            # Let's just take the middle parts as name
            if parts[0] == "Attendance":
                # Attendance_Name_Date_Time.jpg
                # Date and Time are last two parts
                if len(parts) >= 4:
                     name_parts = parts[1:-2]
                     display_name = " ".join(name_parts)
                else:
                    display_name = parts[1]
            
        
        filepath = os.path.join(PHOTOS_DIR, filename)
        mod_time = os.path.getmtime(filepath)
        dt = datetime.fromtimestamp(mod_time)
        timestamp_display = dt.strftime("%Y-%m-%d %H:%M:%S")

        photo_data.append({
            'filename': filename,
            'name': display_name,
            'timestamp': timestamp_display,
            'url': f'/photos/{filename}'
        })
        
    return jsonify(photo_data)

@app.route('/photos/<path:filename>')
def serve_photo(filename):
    return send_from_directory(app.config['PHOTOS_FOLDER'], filename)

if __name__ == '__main__':
    # Listen on verified port
    import socket
    def get_ip_address():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    host_ip = get_ip_address()
    print("Starting Attendance Viewer Server...")
    print(f" * Local:   http://localhost:5000")
    print(f" * Network: http://{host_ip}:5000 (Use this on your mobile)")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
