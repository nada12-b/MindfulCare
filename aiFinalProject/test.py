from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

import google.generativeai as genai
import whisper
import base64
import json
import logging
import tempfile
import os
import aiohttp
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def serve_test_html():
    return FileResponse(Path(__file__).parent / "test.html")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
class AudioMessage(BaseModel):
    audio_data: str

class AgentRAG:
    def __init__(self):
        self.search_client = SearchClient(
            endpoint=os.getenv("SEARCH_ENDPOINT"),
            index_name=os.getenv("INDEX_NAME"),
            credential=AzureKeyCredential(os.getenv("SEARCH_KEY"))
        )
        
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-pro')
        
        self.whisper_model = whisper.load_model("base")
        
        self.did_api_key = os.getenv("DID_API_KEY")
        self.agent_id = ("AGENT_ID")

    async def process_message(self, message):
        """Process the user message and generate a response."""
        try:
            search_results = list(self.search_client.search(
                search_text=message,
                select=["content", "title"],
                top=3
            ))
            
            context_text = "\n\n".join(
                f"Title: {doc['title']}\nContent: {doc['content']}"
                for doc in search_results
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
            - Keep responses concise and natural for speech.
            - Limit response to 2-3 sentences for better avatar interaction.
            """
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            return "I'm sorry, I encountered an issue. Can you please rephrase or try again?"

    async def process_audio(self, audio_data: str):
        """Process audio data and return transcription."""
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

    async def create_avatar_stream(self, text: str):
        """Create a D-ID avatar talk session."""
        url = "https://api.d-id.com/talks"
        headers = {
            "Authorization": f"Basic {self.did_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "script": {
                "type": "text",
                "input": text,
                "provider": {
                    "type": "microsoft",
                    "voice_id": "en-US-SaraNeural"  
                }
            },
            "config": {
                "fluent": True,
                "pad_audio": 0,
                "driver_expressions": {
                    "expressions": [
                        {"expression": "neutral", "start_frame": 0, "intensity": 0}
                    ]
                }
            },
            "source_url": "https://create-images-results.d-id.com/api_docs/assets/noelle.jpeg"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 201:
                    error_text = await response.text()
                    logging.error(f"D-ID API Error: {error_text}")
                    raise HTTPException(status_code=response.status, detail=f"Failed to create avatar talk: {error_text}")
                result = await response.json()
                return result.get("id")

    async def get_avatar_stream_url(self, talk_id: str):
        """Get the URL for the avatar stream."""
        url = f"https://api.d-id.com/talks/{talk_id}"
        headers = {
            "Authorization": f"Basic {self.did_api_key}"
        }

        max_retries = 10
        retry_delay = 1  

        for _ in range(max_retries):
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("status") == "done":
                            return result.get("result_url")
                    await asyncio.sleep(retry_delay)

        raise HTTPException(status_code=408, detail="Timeout waiting for avatar stream")

agent = AgentRAG()

@app.websocket("/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if "audio_data" in message_data:
                transcribed_text = await agent.process_audio(message_data["audio_data"])
                response = await agent.process_message(transcribed_text)
            else:
                response = await agent.process_message(message_data["text"])


            talk_id = await agent.create_avatar_stream(response)
            stream_url = await agent.get_avatar_stream_url(talk_id)
            
            await websocket.send_json({
                "response": response,
                "avatar_url": stream_url,
                "transcription": transcribed_text if "audio_data" in message_data else None
            })
                
        except Exception as e:
            logging.error(f"WebSocket error: {str(e)}")
            await websocket.send_json({"error": str(e)})
            break

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)