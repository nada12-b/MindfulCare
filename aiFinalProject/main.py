import asyncio
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
import time
import os 

# Initialize FastAPI app
app = FastAPI()

load_dotenv()

search_endpoint = os.getenv("SEARCH_ENDPOINT")
index_name = os.getenv("INDEX_NAME")
search_key = os.getenv("SEARCH_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_endpoint = os.getenv("OPENAI_ENDPOINT")

# Token Bucket for rate limiting
class TokenBucket:
    def __init__(self, tokens_per_minute):
        self.tokens = tokens_per_minute
        self.capacity = tokens_per_minute
        self.rate = tokens_per_minute / 60
        self.last_refill_time = time.monotonic()  # Use time.monotonic() for initialization

    async def acquire(self):
        now = time.monotonic()  # Use time.monotonic() here instead of asyncio.get_running_loop().time()
        elapsed = now - self.last_refill_time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill_time = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


# Initialize clients
search_client = SearchClient(
    endpoint=search_endpoint,
    index_name=index_name,
    credential=AzureKeyCredential(search_key)
)
token_bucket = TokenBucket(tokens_per_minute=150)

# Message input model
class Message(BaseModel):
    message: str

@app.post("/process_message")
async def process_message(input: Message):
    message = input.message

    try:
        # Check rate limit
        if not await token_bucket.acquire():
            raise HTTPException(status_code=429, detail="The service is currently busy. Please try again later.")

        # Search custom knowledge base
        context = search_client.search(search_text=message, select=["content", "title"], top=1)
        context_text = "\n".join(
            f"Title: {doc['title']}\nContent: {doc['content']}" for doc in context
        ) if context else "No relevant context found."

        data_source = "your custom knowledge base" if context_text.strip() else "general knowledge"

        # Prepare OpenAI API request
        headers = {"Content-Type": "application/json", "api-key": openai_api_key}
        payload = {
            "messages": [
                {"role": "system", "content": "You are a friendly and helpful mental health advisor."},
                {"role": "user", "content": f"Context: {context_text}\nQuestion: {message}"}
            ],
            "temperature": 0.7,
            "max_tokens": 300,
            "top_p": 0.95,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }

        # OpenAI API request with retries
        async with httpx.AsyncClient() as client:
            for _ in range(3):
                response = await client.post(openai_endpoint, headers=headers, json=payload, timeout=10)
                if response.status_code == 200:
                    ai_response = response.json()["choices"][0]["message"]["content"]
                    return {"response": ai_response, "source": data_source}
                elif response.status_code == 429:  # Rate limit
                    await asyncio.sleep(1)
                else:
                    raise HTTPException(status_code=response.status_code, detail=response.text)

        raise HTTPException(status_code=500, detail="Failed to process your request. Please try again later.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
