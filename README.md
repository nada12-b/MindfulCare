# AI-Powered Mental Health Advisor

An interactive and empathetic mental health assistant designed to provide accessible support. This application integrates advanced AI technologies for real-time transcription, context-aware responses, and avatar-based interactions.

---

## Features
- **Speech-to-Text Transcription**: Converts user audio input into text using Whisper.
- **AI-Driven Responses**: Generates empathetic and contextually relevant replies with the Gemini AI model.
- **Avatar Interaction**: Utilizes D-ID API for engaging video avatar responses.
- **Knowledge Retrieval**: Fetches context-aware answers from Azure Search.

---

## Technologies Used
- **Backend**: FastAPI
- **Frontend**: HTML, JavaScript, TailwindCSS
- **AI Models**: Whisper (speech-to-text), Gemini (response generation), Azure Search (knowledge retrieval)
- **Avatar Integration**: D-ID API

---

## Prerequisites
- Python 3.9 or higher
- Git
- API keys for:
  - Gemini
  - D-ID
  - Azure Search

---

## Installation and Setup

### Clone the Repository
```bash
git clone https://github.com/nada12-b/MindfulCare.git
cd aiFinalProjecttest
```

### Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate   # For Linux/macOS
venv\Scripts\activate      # For Windows
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Set Up Environment Variables
Create a `.env` file in the root directory and add the following:
```
GEMINI_API_KEY=your_gemini_api_key
DID_API_KEY=your_did_api_key
SEARCH_ENDPOINT=your_azure_search_endpoint
SEARCH_KEY=your_azure_search_key
INDEX_NAME=your_index_name
```

---

## Running the Application

### 1. Run the Backend (backend.py)
Start the backend server:
```bash
python backend.py
```
The backend will run on [http://127.0.0.1:8000](http://127.0.0.1:8000).

### 2. Run the backend (test.py)
Start the frontend server:
```bash
python test.py
```
The avatar backend will run on [http://127.0.0.1:8001](http://127.0.0.1:8001).

---

## Usage
1. Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
2. Use the chat interface to interact with the AI assistant:
   - Type messages or use the microphone button to send audio inputs.
   - Watch the avatar respond in real-time while the transcription appears in the chat.
3. The backend handles:
   - Speech-to-text conversion.
   - AI response generation.
   - Avatar video generation.

---



## Contribution
Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add a descriptive message"
   ```
4. Push to your branch:
   ```bash
   git push origin feature-name
   ```
5. Create a pull request.

---


## Disclaimer
This application is not a substitute for professional medical advice. For serious mental health concerns, consult a licensed professional or emergency services.
