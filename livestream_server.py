import cv2
import subprocess
import os
from flask import Flask, send_from_directory, Response

app = Flask(__name__)

# Directory to store HLS stream files
HLS_DIR = 'hls_stream'
if not os.path.exists(HLS_DIR):
    os.makedirs(HLS_DIR)

# FFmpeg command to generate HLS stream from piped input
ffmpeg_cmd = [
    'ffmpeg',
    '-y',  # overwrite output files
    '-f', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', '640x480',  # frame size
    '-r', '30',  # frame rate
    '-i', '-',  # input from stdin
    '-c:v', 'libx264',
    '-preset', 'veryfast',
    '-f', 'hls',
    '-hls_time', '2',
    '-hls_list_size', '3',
    '-hls_flags', 'delete_segments',
    os.path.join(HLS_DIR, 'index.m3u8')
]

# Start ffmpeg subprocess
ffmpeg_process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

def generate_frames():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open video device")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # Resize frame to 640x480
            frame = cv2.resize(frame, (640, 480))
            # Write raw frame to ffmpeg stdin
            ffmpeg_process.stdin.write(frame.tobytes())
    except GeneratorExit:
        pass
    finally:
        cap.release()
        ffmpeg_process.stdin.close()
        ffmpeg_process.wait()

@app.route('/hls/<path:filename>')
def hls_files(filename):
    return send_from_directory(HLS_DIR, filename)

@app.route('/stream')
def stream():
    # This endpoint just serves a simple HTML page with video player
    html = """
    <html>
    <head><title>Livestream</title></head>
    <body>
    <video id="video" width="640" height="480" controls autoplay></video>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <script>
    var video = document.getElementById('video');
    if(Hls.isSupported()) {
        var hls = new Hls();
        hls.loadSource('/hls/index.m3u8');
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED,function() {
            video.play();
        });
    }
    else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = '/hls/index.m3u8';
        video.addEventListener('loadedmetadata',function() {
            video.play();
        });
    }
    </script>
    </body>
    </html>
    """
    return Response(html, mimetype='text/html')

if __name__ == '__main__':
    import threading
    # Start frame capture in a separate thread
    t = threading.Thread(target=generate_frames)
    t.daemon = True
    t.start()
    # Run Flask app
    app.run(host='0.0.0.0', port=5000)
