import os
import yt_dlp
import sqlite3
from urllib.parse import urlparse, parse_qs
import time
import json
import threading

def get_youtube_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if 'v' in parse_qs(parsed_url.query):
            return parse_qs(parsed_url.query)['v'][0]
    return None

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
                     title TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.close()

def generate_progress(task_id, progress):
    while True:
        if task_id in progress:
            yield f"data: {json.dumps(progress[task_id])}\n\n"
            if progress[task_id]['status'] == 'complete':
                break
        time.sleep(1)

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

def process_video(task_id, youtube_url, text_prompt, progress, AudioTranscriber, OpenAIAssistant):
    try:
        progress[task_id] = {'status': 'downloading', 'progress': 10}
        
        # Get video info
        with yt_dlp.YoutubeDL({'skip_download': True}) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            video_title = info.get('title', 'Untitled Video')
            thumbnail_url = info.get('thumbnail', '')
        
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
            conn.execute('INSERT INTO responses (youtube_url, text_prompt, transcription, response, thumbnail_url, title) VALUES (?, ?, ?, ?, ?, ?)',
                         (youtube_url, text_prompt, transcription, response, thumbnail_url, video_title))
            conn.commit()
            conn.close()
            
            progress[task_id] = {'status': 'complete', 'progress': 100, 'transcription': transcription, 'response': response}
        else:
            progress[task_id] = {'status': 'error', 'message': 'Failed to download the audio'}
    except Exception as e:
        progress[task_id] = {'status': 'error', 'message': str(e)}
