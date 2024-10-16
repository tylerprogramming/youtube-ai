from flask import Flask, request, jsonify, Response
import json
from flask_cors import CORS
import yt_dlp
import os
import sqlite3
from urllib.parse import urlparse, parse_qs
import uuid

from audio_transcriber_agent import AudioTranscriber
from summarize_me import OpenAIAssistant

app = Flask(__name__)
CORS(app)

# Database setup
def get_db_connection():
    conn = sqlite3.connect('youtube.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS transcription
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     youtube_url TEXT NOT NULL,
                     text_prompt TEXT NOT NULL,
                     transcription TEXT NOT NULL,
                     thumbnail_url TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS summary
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     transcription_id INTEGER NOT NULL,
                     summary TEXT NOT NULL,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (transcription_id) REFERENCES transcription (id))''')

    conn.execute('''CREATE TABLE IF NOT EXISTS chat_session
                    (id TEXT PRIMARY KEY,
                     name TEXT NOT NULL DEFAULT 'Unnamed Session',
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    conn.execute('''CREATE TABLE IF NOT EXISTS chat_message
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     session_id TEXT NOT NULL,
                     message_type TEXT NOT NULL,
                     content TEXT NOT NULL,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (session_id) REFERENCES chat_session (id))''')
    
    conn.commit()
    conn.close()

def add_name_column_if_not_exists():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(chat_session)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'name' not in columns:
        cursor.execute("ALTER TABLE chat_session ADD COLUMN name TEXT NOT NULL DEFAULT 'Unnamed Session'")
    conn.commit()
    conn.close()

# Make sure to call init_db() and add_name_column_if_not_exists() when the app starts
if __name__ == '__main__':
    init_db()
    add_name_column_if_not_exists()
    app.run(debug=True, port=5050)

def extract_video_id(url):
    # Simple extraction, you might want to use a more robust method
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1]
    return None

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

def get_youtube_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if 'v' in parse_qs(parsed_url.query):
            return parse_qs(parsed_url.query)['v'][0]
    return None

@app.route('/api/start_session', methods=['POST', 'OPTIONS', 'GET'])
def start_session():
    if request.method == 'OPTIONS':
        return '', 204
    
    print("Received start_session request")
    print("Request data:", request.json)

    data = request.json
    session_name = data.get('name', 'Unnamed Session')
    session_id = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute('INSERT INTO chat_session (id, name) VALUES (?, ?)', (session_id, session_name))
    conn.commit()
    conn.close()
    return jsonify({"session_id": session_id})

@app.route('/api/transcribe', methods=['POST'])
def transcribe_and_summarize():
    if request.method == 'OPTIONS':
        return '', 204
    print("Received transcribe request")
    print("Request data:", request.json)
    data = request.json
    url = data['url']
    prompt = data['prompt']
    session_id = data['session_id']

    def generate():
        yield json.dumps({"status": "downloading", "progress": 0}) + "\n"
        
        downloaded_file = download_youtube_audio(url)
        yield json.dumps({"status": "transcribing", "progress": 30}) + "\n"
        
        if not downloaded_file:
            yield json.dumps({"error": "Failed to download audio"}) + "\n"
            return

        transcriber = AudioTranscriber()
        transcription = transcriber.transcribe_audio(downloaded_file)
        
        yield json.dumps({"status": "summarizing", "progress": 70}) + "\n"

        assistant = OpenAIAssistant(transcription)
        summary = assistant.ask_question(prompt)

        yield json.dumps({"status": "summarized", "progress": 100}) + "\n"
        
        conn = get_db_connection()
        video_id = get_youtube_video_id(url)
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/0.jpg" if video_id else None
        
        cursor = conn.cursor()
        cursor.execute('INSERT INTO transcription (youtube_url, text_prompt, transcription, thumbnail_url) VALUES (?, ?, ?, ?)',
                        (url, prompt, transcription, thumbnail_url))
        transcription_id = cursor.lastrowid
        
        cursor.execute('INSERT INTO summary (transcription_id, summary) VALUES (?, ?)',
                        (transcription_id, summary))
        
        cursor.execute('INSERT INTO chat_message (session_id, message_type, content) VALUES (?, ?, ?)',
                        (session_id, 'user', prompt))
        cursor.execute('INSERT INTO chat_message (session_id, message_type, content) VALUES (?, ?, ?)',
                        (session_id, 'bot', summary))
        
        conn.commit()
        conn.close()

        yield json.dumps({
            "status": "complete",
            "progress": 100,
            "summary": summary,
            "title": f"Video ID: {video_id}"
        }) + "\n"

    return Response(generate(), mimetype='application/json')

@app.route('/api/chat_history', methods=['GET'])
def get_chat_history():
    session_id = request.args.get('session_id')
    if not session_id or session_id == 'undefined':
        return jsonify({
            'messages': [],
            'has_transcript': False
        }), 200  # Return an empty result with 200 OK status

    conn = get_db_connection()
    messages = conn.execute('SELECT message_type, content FROM chat_message WHERE session_id = ? ORDER BY created_at', (session_id,)).fetchall()
    
    # Check if there's a transcript for this session
    transcript = conn.execute('SELECT transcription FROM transcription WHERE id IN (SELECT transcription_id FROM summary WHERE id IN (SELECT MAX(id) FROM summary WHERE transcription_id IN (SELECT transcription_id FROM chat_message WHERE session_id = ?)))', (session_id,)).fetchone()
    
    conn.close()
    return jsonify({
        'messages': [{'type': msg['message_type'], 'content': msg['content']} for msg in messages],
        'has_transcript': bool(transcript)
    })

@app.route('/api/sessions', methods=['GET'])
def get_available_sessions():
    print("Received get_available_sessions request")
    try:
        conn = get_db_connection()
        sessions = conn.execute('SELECT id, name, created_at FROM chat_session ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([{'id': session['id'], 'name': session['name'], 'created_at': session['created_at']} for session in sessions])
    except sqlite3.OperationalError as e:
        print(f"Database error: {str(e)}")
        return jsonify({"error": "Database error", "message": str(e)}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Unexpected error", "message": str(e)}), 500

@app.route('/api/ask_question', methods=['POST', 'OPTIONS'])
def ask_question():
    if request.method == 'OPTIONS':
        return '', 204
    print("Received ask_question request")
    print("Request data:", request.json)
    data = request.json
    session_id = data['session_id']
    question = data['question']

    conn = get_db_connection()
    transcript = conn.execute('SELECT transcription FROM transcription WHERE id IN (SELECT transcription_id FROM summary WHERE id IN (SELECT MAX(id) FROM summary WHERE transcription_id IN (SELECT transcription_id FROM chat_message WHERE session_id = ?)))', (session_id,)).fetchone()

    if not transcript:
        # If there's no transcript, we'll just respond with a generic message
        answer = "I'm sorry, but there's no transcript available for this session yet. Please provide a YouTube URL first to transcribe and summarize the content."
    else:
        assistant = OpenAIAssistant(transcript['transcription'])
        answer = assistant.ask_question(question)

    cursor = conn.cursor()
    cursor.execute('INSERT INTO chat_message (session_id, message_type, content) VALUES (?, ?, ?)',
                    (session_id, 'user', question))
    cursor.execute('INSERT INTO chat_message (session_id, message_type, content) VALUES (?, ?, ?)',
                    (session_id, 'bot', answer))
    conn.commit()
    conn.close()

    return jsonify({"answer": answer})
