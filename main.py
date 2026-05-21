"""Read a PDF with PyMuPDF, generate MCQs with Groq, write two .txt files."""

import os
import sys

import fitz
from dotenv import load_dotenv
from groq import Groq
from tqdm import tqdm

load_dotenv()

# --- edit these ---
PDF_PATH = "NPTEL CLOUD.pdf"
MCQ_COUNT = 10
MODEL = "llama-3.3-70b-versatile"
OUT_DIR = "output"
TEMPERATURE = 0.4
# ------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

SYSTEM_PROMPT = """You create multiple-choice questions from study material.
Output exactly two sections with these headers on their own lines:

=== MCQS ===
(numbered questions, each with options A–D on separate lines)

=== ANSWER KEY ===
(numbered lines like: 1. B) brief explanation)"""


def read_pdf(path: str) -> str:
    doc = fitz.open(path)
    pages = []
    for i in tqdm(range(doc.page_count), desc="Reading PDF", unit="page"):
        pages.append(doc[i].get_text())
    doc.close()
    return "\n".join(pages).strip()


def generate_mcqs(text: str) -> str:
    if not GROQ_API_KEY:
        sys.exit("Set GROQ_API_KEY in your .env file.")

    client = Groq(api_key=GROQ_API_KEY)
    user = f"Create {MCQ_COUNT} multiple-choice questions from this text.\n\n{text[:120_000]}"

    with tqdm(total=1, desc="Generating MCQs (Groq)", bar_format="{l_bar}{bar}| {elapsed}") as bar:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=TEMPERATURE,
        )
        bar.update(1)

    return response.choices[0].message.content or ""


def split_output(raw: str) -> tuple[str, str]:
    marker_mcqs = "=== MCQS ==="
    marker_answers = "=== ANSWER KEY ==="

    if marker_mcqs not in raw or marker_answers not in raw:
        return raw.strip(), "(Could not split answer key — check model output.)"

    _, rest = raw.split(marker_mcqs, 1)
    mcqs_part, answers_part = rest.split(marker_answers, 1)
    return mcqs_part.strip(), answers_part.strip()


def main() -> None:
    if not os.path.isfile(PDF_PATH):
        sys.exit(f"PDF not found: {PDF_PATH}")

    text = read_pdf(PDF_PATH)
    if not text:
        sys.exit("No text found in PDF.")

    raw = generate_mcqs(text)
    mcqs, answers = split_output(raw)

    os.makedirs(OUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(PDF_PATH))[0]
    paths = [
        os.path.join(OUT_DIR, f"{base}_mcqs.txt"),
        os.path.join(OUT_DIR, f"{base}_answer_key.txt"),
    ]

    for path, content in tqdm(
        zip(paths, [mcqs, answers]),
        total=2,
        desc="Writing files",
        unit="file",
    ):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        tqdm.write(f"Saved {path}")


if __name__ == "__main__":
    main()
