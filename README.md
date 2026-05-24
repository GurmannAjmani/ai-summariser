# AI Study Assistant

Studying is hard. Studying smart is harder. This tool tries to bridge that gap — it takes any PDF you throw at it and turns it into a full suite of exam-prep material using a large language model on the backend. Upload your notes, get back summaries, revision sheets, MCQ quizzes, flashcards, and even auto-generated diagrams. There's also a Q&A mode where you can ask anything directly from the document.

Built for Problem Statement 1: **AI Study Assistant for Exam Preparation**.

---

## Demo

Watch it in action here: [https://youtu.be/1u7I4lTwHAM](https://youtu.be/1u7I4lTwHAM)

---

## Selected Problem Statement

**Problem Statement 1 — AI Study Assistant for Exam Preparation**

Build an AI-powered study assistant where students can upload notes, PDFs, and study materials to ask questions directly from documents, generate summaries and flashcards, create MCQs and revision material, and simplify exam preparation using AI.

Domains: Generative AI, NLP, EdTech Solutions.

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| Language | Python 3.11+ |
| LLM Inference | Groq API (Llama 3.3-70B Versatile) |
| PDF Parsing | PyMuPDF (fitz) |
| Diagram Rendering | mermaid.ink (public API) |
| Config | python-dotenv |

---

## Backend Architecture

The codebase is split into two clear layers — which honestly made development a lot less painful.

`main.py` is a pure function library. No UI logic lives there. It handles PDF text extraction, all Groq API calls, Mermaid diagram rendering, and PDF assembly. Every function takes explicit inputs and returns explicit outputs — nothing fancy, nothing hidden.

`app.py` is the Streamlit frontend. It imports from `main.py`, manages session state (so generated content survives tab switches), and handles all user interaction. Each feature tab is independent; generating a summary does not trigger flashcard generation. The user picks what they want.

```
app.py (Streamlit UI)
    |
    |-- session_state (per-feature caching)
    |
    v
main.py (core logic)
    |-- read_pdf()           → PyMuPDF text extraction
    |-- ask_groq()           → Groq API wrapper
    |-- generate_summary()   → structured document summary
    |-- generate_revision()  → bullet-point revision notes
    |-- generate_mcqs()      → MCQ + answer key (split by markers)
    |-- generate_flashcards() → Q: / A: formatted pairs
    |-- generate_diagrams()  → Mermaid code from LLM
    |-- render_mermaid_to_png() → mermaid.ink HTTP call
    |-- diagrams_to_pdf_bytes() → PNG-to-PDF via PyMuPDF
    |-- answer_question()    → context-aware Q&A
```

---

## Implementation Approach

The workflow is deliberately linear for each feature — upload PDF, click generate, get output. No magic pipelines.

**PDF Ingestion**
PyMuPDF opens the uploaded file from memory (no disk writes needed), iterates through every page, concatenates the text, and caps it at 120,000 characters to stay within the LLM context window. This is the raw material for everything else.

**LLM Generation**
All generation flows through a single `ask_groq()` function. Each feature has its own system prompt — tightly worded to constrain the model's output format. The MCQ prompt, for instance, forces the model to output two clearly delimited sections (`=== MCQS ===` and `=== ANSWER KEY ===`) which are then split programmatically. Flashcards use a `Q:` / `A:` line format that's easy to parse with a simple loop.

**MCQ Quiz Mode**
The parsed questions are rendered as a Streamlit form with radio buttons. On submission, each answer is compared against the parsed answer key. The user sees per-question correct/wrong feedback and a final score. Fairly straightforward — no state gymnastics required.

**Diagrams**
The LLM generates raw Mermaid syntax. That code gets base64-encoded and sent to `mermaid.ink` as a GET request. The PNG response is then collected, and PyMuPDF assembles all images into a single downloadable PDF.

**Q&A**
The full extracted text is passed alongside the user's question in each request. The model is instructed to answer strictly from the provided document — so it doesn't hallucinate content from outside the PDF.

---

## Features

- PDF upload with in-memory text extraction
- Document summary — downloadable as PDF
- Revision notes — structured bullet points, downloadable as PDF
- Interactive MCQ quiz — answer, submit, and see what you got wrong
- Flashcards — question shown by default, answer revealed on click
- Mermaid diagram generation — 3 auto-generated diagrams saved as a PDF
- Document Q&A — ask anything, get an answer grounded in the uploaded text
- Per-feature generation — each tab has its own button, nothing is forced

---

## APIs and Models Used

**Groq API**
- Endpoint: `https://api.groq.com`
- Model: `llama-3.3-70b-versatile`
- Used for all text generation (summaries, MCQs, revision notes, flashcards, diagrams, Q&A)
- Requires an API key (free tier available at console.groq.com)
- Free tier rate limits: ~30 requests/minute, ~14,400 requests/day

**mermaid.ink**
- Public API, no key required
- Converts base64-encoded Mermaid syntax to PNG images
- Endpoint format: `https://mermaid.ink/img/{base64_encoded_mermaid_code}`

---

## Setup Instructions

### Prerequisites

- Python 3.11 or above
- A Groq API key — get one free at [console.groq.com](https://console.groq.com)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd "ai summariser"
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the project root (see `.env.example` below):

```
GROQ_API_KEY=your_key_here
```

### 5. Run the app

```powershell
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Environment Variables

Create a `.env` file in the project root with the following:

```
GROQ_API_KEY=gsk_your_groq_key_here
```

| Variable | Description | Required |
|---|---|---|
| `GROQ_API_KEY` | Your Groq API key for LLM inference | Yes |

The API key can also be entered directly in the app sidebar if you prefer not to use a `.env` file.

---

## Installation Summary

```
requirements.txt
├── pymupdf          # PDF parsing and PDF generation
├── groq             # Groq Python SDK
├── python-dotenv    # .env file loading
├── tqdm             # Progress bars (CLI utility, retained for compatibility)
└── streamlit        # Web UI framework
```
