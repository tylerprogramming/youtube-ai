# YouTube Transcript AI Assistant

This project is a YouTube video transcript analyzer that uses AI to provide summaries and answer questions about the video content.

## How it works

It is a single Flask app with server-rendered pages (Jinja templates, Bootstrap, jQuery). There is no separate frontend.

1. You paste a YouTube URL and a question or prompt.
2. `yt-dlp` downloads the audio as MP3 (through FFmpeg).
3. OpenAI `gpt-transcribe` transcribes it.
4. OpenAI `gpt-6-luna` answers your prompt using the transcript as context.
5. The result is saved to a local SQLite database (`youtube_responses.db`), and progress streams to the page over server-sent events.

Key files:
- `app.py`: Flask routes (`/`, `/results`, `/get_thumbnail`, `/process_with_progress`, `/progress/<task_id>`)
- `utilities.py`: YouTube download, SQLite setup, and the background processing job
- `stt_agent.py`: speech-to-text (`AudioTranscriber`)
- `summarize_me.py`: question answering over the transcript (`OpenAIAssistant`)
- `templates/index.html`, `templates/results.html`, `static/css/`: the UI

## Setup and Installation

Requirements: Python 3.11+, [FFmpeg](https://ffmpeg.org/download.html) on your PATH (yt-dlp uses it to extract MP3 audio), and an OpenAI API key.

1. Clone the repository:
   ```
   git clone https://github.com/tylerprogramming/youtube-ai.git
   cd youtube-ai
   ```

2. Create a virtual environment and install the dependencies:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```
   No YouTube API key is needed; yt-dlp fetches the video directly.

## Running the Application

1. Start the app:
   ```
   python app.py
   ```

2. Open your browser and navigate to `http://localhost:5051`.

## Usage

1. Enter a YouTube video URL and what you want to know about it.
2. The page shows progress while the audio downloads, gets transcribed, and gets analyzed.
3. The transcript and the AI's answer appear when it finishes, with copy buttons.
4. **View All Results** (`/results`) lists every saved run. The committed `youtube_responses.db` already has some example runs in it; delete the file to start fresh (it is recreated on startup).

Downloaded MP3 files are saved in the project folder.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
