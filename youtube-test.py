import os
import yt_dlp
from stt_agent import AudioTranscriber
from dotenv import load_dotenv
from summarize_me import OpenAIAssistant
from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from flask import Response
import time
import json
import threading

load_dotenv()

app = Flask(__name__)

# Database setup
def get_db_connection():
    conn = sqlite3.connect('youtube_responses.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS responses
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     youtube_url TEXT NOT NULL,
                     text_prompt TEXT NOT NULL,
                     transcription TEXT NOT NULL,
                     response TEXT NOT NULL,
                     thumbnail_url TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.close()

init_db()

progress = {}

def generate_progress(task_id):
    while True:
        if task_id in progress:
            yield f"data: {json.dumps(progress[task_id])}\n\n"
            if progress[task_id]['status'] == 'complete':
                break
        time.sleep(1)

@app.route('/progress/<task_id>')
def task_progress(task_id):
    return Response(generate_progress(task_id), mimetype='text/event-stream')

def download_youtube_audio(url, output_path='.'):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'prefer_ffmpeg': True,
        'keepvideo': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_filename = os.path.splitext(filename)[0] + '.mp3'
            
            if os.path.exists(mp3_filename):
                print(f"Audio download complete: {mp3_filename}")
                return mp3_filename
            else:
                print(f"Error: MP3 file not found at {mp3_filename}")
                return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

@app.route('/', methods=['GET'])
def home():
    conn = get_db_connection()
    total_videos = conn.execute('SELECT COUNT(*) FROM responses').fetchone()[0]
    conn.close()
    return render_template('index.html', total_videos=total_videos)

@app.route('/results')
def results():
    print("Entering results route")  # Debug print
    conn = get_db_connection()
    responses = conn.execute('SELECT * FROM responses ORDER BY created_at DESC').fetchall()
    conn.close()
    print(f"Number of responses: {len(responses)}")  # Debug print
    return render_template('results.html', responses=responses)

@app.route('/debug_results')
def debug_results():
    return render_template('results.html', responses=[])

@app.route('/get_thumbnail', methods=['POST'])
def get_thumbnail():
    youtube_url = request.json['youtube_url']
    video_id = get_youtube_video_id(youtube_url)
    if video_id:
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/0.jpg"
        return jsonify({'thumbnail_url': thumbnail_url})
    else:
        return jsonify({'error': 'Invalid YouTube URL'}), 400

def get_youtube_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if 'v' in parse_qs(parsed_url.query):
            return parse_qs(parsed_url.query)['v'][0]
    return None

def process_video(task_id, youtube_url, text_prompt):
    try:
        progress[task_id] = {'status': 'downloading', 'progress': 10}
        downloaded_file = download_youtube_audio(youtube_url)
        
        if downloaded_file:
            progress[task_id] = {'status': 'transcribing', 'progress': 40}
            transcriber = AudioTranscriber()
            transcription = transcriber.transcribe_audio(downloaded_file)
            
            progress[task_id] = {'status': 'analyzing', 'progress': 70}
            assistant = OpenAIAssistant(transcription)
            response = assistant.ask_question(text_prompt)
            
            progress[task_id] = {'status': 'saving', 'progress': 90}
            # Save to database
            conn = get_db_connection()
            video_id = get_youtube_video_id(youtube_url)
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/0.jpg" if video_id else None
            conn.execute('INSERT INTO responses (youtube_url, text_prompt, transcription, response, thumbnail_url) VALUES (?, ?, ?, ?, ?)',
                         (youtube_url, text_prompt, transcription, response, thumbnail_url))
            conn.commit()
            conn.close()
            
            progress[task_id] = {'status': 'complete', 'progress': 100, 'transcription': transcription, 'response': response}
        else:
            progress[task_id] = {'status': 'error', 'message': 'Failed to download the audio'}
    except Exception as e:
        progress[task_id] = {'status': 'error', 'message': str(e)}

@app.route('/process_with_progress', methods=['POST'])
def process_with_progress():
    youtube_url = request.form['youtube_url']
    text_prompt = request.form['text_prompt']
    
    task_id = str(time.time())  # Generate a unique task ID
    progress[task_id] = {'status': 'starting', 'progress': 0}
    
    # Start processing in a separate thread
    thread = threading.Thread(target=process_video, args=(task_id, youtube_url, text_prompt))
    thread.start()
    
    return jsonify({'task_id': task_id})

if __name__ == '__main__':
    app.run(debug=True, port=5051)


