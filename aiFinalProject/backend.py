from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import google.generativeai as genai
from dotenv import load_dotenv
import whisper
import base64
import json
import logging
import tempfile
import os
from pydantic import BaseModel
from pathlib import Path

logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_FILE_PATH = BASE_DIR / "frontend.html"

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    if FRONTEND_FILE_PATH.exists():
        return FileResponse(FRONTEND_FILE_PATH)
    return HTMLResponse(
        content="<h1>Frontend not found. Please place the frontend.html file in the same directory as backend.py.</h1>",
        status_code=404,
    )

class AudioMessage(BaseModel):
    audio_data: str

class AgentRAG:
    def __init__(self, search_endpoint, index_name, search_key, gemini_api_key):
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(search_key),
        )
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel("gemini-pro")
        self.whisper_model = whisper.load_model("base")

    async def process_audio(self, audio_data: str):
        try:
            audio_bytes = base64.b64decode(audio_data.split(",")[1] if "," in audio_data else audio_data)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                temp_audio.write(audio_bytes)
                temp_audio.flush()
                temp_audio_path = temp_audio.name
            result = self.whisper_model.transcribe(temp_audio_path)
            os.unlink(temp_audio_path)
            return result["text"]
        except Exception as e:
            logging.error(f"Error processing audio: {str(e)}")
            raise

    async def process_message(self, message: str):
        try:
            context = self.search_client.search(
                search_text=message,
                select=["content", "title"],
                top=3,
            )
            context_text = "\n\n".join(
                f"Title: {doc['title']}\nContent: {doc['content']}" for doc in context
            )
            prompt = f"""
            You are a compassionate and empathetic mental health advisor AI acting like a professional psychologist.
            Your role is to create a warm and friendly environment, provide therapeutic support, and answer questions with 
            kindness and understanding.
            Context:
            {context_text}
            User: {message}
            If the context does not contain an answer:
            - Provide an empathetic response using your knowledge.
            - Avoid technical jargon and prioritize emotional support.
            """
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            return "I'm sorry, I encountered an issue. Can you please rephrase or try again?"

load_dotenv()
agent = AgentRAG(
    search_endpoint=os.getenv("SEARCH_ENDPOINT"),
    index_name=os.getenv("INDEX_NAME"),
    search_key=os.getenv("SEARCH_KEY"),
    gemini_api_key=os.getenv("GEMINI_API_KEY"),
)
@app.get("/avatar", response_class=HTMLResponse)
async def serve_avatar():
    avatar_file = BASE_DIR / "avatar.html"
    if avatar_file.exists():
        return FileResponse(avatar_file)
    return HTMLResponse(
        content="<h1>Avatar page not found.</h1>", status_code=404
    )


@app.websocket("/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            if "audio_data" in message_data:
                transcribed_text = await agent.process_audio(message_data["audio_data"])
                response = await agent.process_message(transcribed_text)
                await websocket.send_json({
                    "transcription": transcribed_text,
                    "response": response,
                })
            elif "text" in message_data:
                response = await agent.process_message(message_data["text"])
                await websocket.send_json({"response": response})
    except WebSocketDisconnect:
        logging.info("WebSocket disconnected.")
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")
        await websocket.send_json({"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)