# PDF → MCQ generator

Reads a PDF with PyMuPDF and uses Groq to write four files in `output/`:

- `<name>_mcqs.txt` — questions
- `<name>_answer_key.txt` — answers
- `<name>_summary.txt` — document summary
- `<name>_revision.txt` — key points, definitions, and brief concept explanations for revision

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
