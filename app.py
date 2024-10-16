import os
from stt_agent import AudioTranscriber
from dotenv import load_dotenv
from summarize_me import OpenAIAssistant
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
import time
import json
import threading
from utilities import (
    get_youtube_video_id, get_db_connection, init_db, generate_progress,
    download_youtube_audio, process_video
)

load_dotenv()

app = Flask(__name__)

init_db()

progress = {}

@app.route('/progress/<task_id>')
def task_progress(task_id):
    return Response(generate_progress(task_id, progress), mimetype='text/event-stream')

@app.route('/', methods=['GET'])
def home():
    conn = get_db_connection()
    total_videos = conn.execute('SELECT COUNT(*) FROM responses').fetchone()[0]
    conn.close()
    return render_template('index.html', total_videos=total_videos)

@app.route('/results')
def results():
    conn = get_db_connection()
    responses = conn.execute('SELECT * FROM responses ORDER BY created_at DESC').fetchall()
    
    total_results = len(responses)
    unique_results = len(set([r['title'] for r in responses]))
    total_transcriptions = conn.execute('SELECT COUNT(*) FROM responses WHERE transcription IS NOT NULL').fetchone()[0]
    latest_timestamp = responses[0]['created_at'].split()[0] if responses else 'N/A'
    
    conn.close()
    
    return render_template('results.html', 
                           responses=responses, 
                           total_results=total_results,
                           unique_results=unique_results,
                           total_transcriptions=total_transcriptions,
                           latest_timestamp=latest_timestamp)

@app.route('/get_thumbnail', methods=['POST'])
def get_thumbnail():
    youtube_url = request.json['youtube_url']
    try:
        ydl_opts = {'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            return jsonify({
                'thumbnail_url': info.get('thumbnail', ''),
                'title': info.get('title', 'Untitled Video')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/process_with_progress', methods=['POST'])
def process_with_progress():
    youtube_url = request.form['youtube_url']
    text_prompt = request.form['text_prompt']
    
    task_id = str(time.time())  # Generate a unique task ID
    progress[task_id] = {'status': 'starting', 'progress': 0}
    
    # Start processing in a separate thread
    thread = threading.Thread(target=process_video, args=(task_id, youtube_url, text_prompt, progress, AudioTranscriber, OpenAIAssistant))
    thread.start()
    
    return jsonify({'task_id': task_id})

if __name__ == '__main__':
    app.run(debug=True, port=5051)





