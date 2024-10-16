from openai import OpenAI

class AudioTranscriber:
    def __init__(self):
        self.client = OpenAI()

    def transcribe_audio(self, file_path):
        with open(file_path, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcription.text
    

# Usage example:
# transcriber = AudioTranscriber()
# transcriber.print_transcription("/path/to/file/audio.mp3")