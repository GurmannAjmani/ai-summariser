# PDF → MCQ generator

Reads a PDF with PyMuPDF, sends the text to Groq, and writes two files:

- `output/<name>_mcqs.txt` — questions
- `output/<name>_answer_key.txt` — answers

## Setup

```powershell
cd "c:\Users\gurma\Desktop\projs\ai summariser"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Put your Groq API key in `.env`:

```
GROQ_API_KEY=gsk_your_key_here
```

Edit `PDF_PATH`, `MCQ_COUNT`, etc. at the top of `main.py`.

## Run

```powershell
python main.py
```
