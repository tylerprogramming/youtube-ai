# YouTube Transcript AI Assistant

This project is a YouTube video transcript analyzer that uses AI to provide summaries and answer questions about the video content.

## Project Structure

The project is divided into two main parts:

1. Backend (Flask API)
2. Frontend (React application)

### Backend

The backend is a Flask application that handles:

- Fetching YouTube video transcripts
- Storing transcript data in a SQLite database
- Interfacing with an AI model (likely GPT-based) to analyze transcripts
- Providing API endpoints for the frontend to interact with

Key files:
- `backend/app.py`: Main Flask application
- `backend/youtube_transcript.py`: YouTube transcript fetching logic
- `backend/database.py`: Database operations
- `backend/ai_interface.py`: AI model integration

### Frontend

The frontend is a React application that provides a user interface for:

- Inputting YouTube video URLs
- Displaying video information and transcripts
- Allowing users to ask questions about the video content
- Showing AI-generated summaries and answers

Key files:
- `frontend/src/App.js`: Main React component
- `frontend/src/components/`: Various React components for UI elements
- `frontend/src/services/api.js`: API calls to the backend

## Setup and Installation

1. Clone the repository:
   ```
   git clone https://github.com/tylerprogramming/youtube-ai.git
   cd youtube-ai
   ```

2. Set up the backend:
   ```
   cd backend
   pip install -r requirements.txt
   ```

3. Set up the frontend:
   ```
   cd frontend
   npm install
   ```

4. Create a `.env` file in the root directory and add your API keys:
   ```
   YOUTUBE_API_KEY=your_youtube_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```

## Running the Application

1. Start the backend server:
   ```
   cd backend
   python app.py
   ```

2. In a new terminal, start the frontend development server:
   ```
   cd frontend
   npm start
   ```

3. Open your browser and navigate to `http://localhost:3000` to use the application.

## Usage

1. Enter a YouTube video URL in the input field.
2. The application will fetch and display the video transcript.
3. You can ask questions about the video content using the provided input field.
4. The AI will analyze the transcript and provide answers or summaries based on your queries.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

