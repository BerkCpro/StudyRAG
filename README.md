# StudyRAG — Smart Study Assistant & FastAPI RAG Platform

**Advanced Computer Programming — Final Project**

StudyRAG is a FastAPI-based educational platform that lets students upload lecture PDFs and generate page-cited answers, quizzes, flashcards, cheat sheets, and interactive mind maps.

## Team
- **Berk Cezik** (`23091390021`)
- **Muhammet Emin Çelik** (`23091390031`)
- **Ali Süleyman Biten** (`23091390011`)
- **Yusuf İshak Alkaş** (`23091390035`)

## Tech Stack
- **Backend:** FastAPI, Uvicorn, Pydantic v2
- **Vector Search (RAG):** Qdrant (local storage)
- **AI Models:** Google Gemini API (5-model automatic fallback chain)
- **PDF Processing:** PyMuPDF (`pymupdf`)
- **Caching:** SQLite (`sqlite3`)
- **Frontend:** Single-file responsive web UI (`index.html`, TR/EN, Dark/Light system theme)

## Setup & Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file from `.env.example` and add your free Gemini API key:
   ```bash
   copy .env.example .env
   ```
   Then set `GEMINI_API_KEY=your_api_key_here` inside `.env` (or pass it as an environment variable).

3. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

4. Open in browser:
   - **Web App:** `http://127.0.0.1:8000`
   - **Swagger API Docs:** `http://127.0.0.1:8000/docs`
