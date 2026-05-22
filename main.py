"""Read a PDF with PyMuPDF, generate study files with Groq."""

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
FLASHCARD_COUNT = 10
MODEL = "llama-3.3-70b-versatile"
OUT_DIR = "output"
TEMPERATURE = 0.4
MAX_TEXT_CHARS = 120_000
# ------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

MCQ_SYSTEM = """You create multiple-choice questions from study material.
Output exactly two sections with these headers on their own lines:

=== MCQS ===
(numbered questions, each with options A–D on separate lines)

=== ANSWER KEY ===
(numbered lines like: 1. B) brief explanation)"""

SUMMARY_SYSTEM = """You summarize academic or technical documents clearly and accurately.
Write a structured summary: main topic, key sections, and takeaways.
Use short paragraphs and bullet points where helpful. No MCQs."""

REVISION_SYSTEM = """You create revision notes from study material for exam prep.
Include:
- Important points (bullets)
- Key terms with definitions
- Brief explanations of core concepts

Use clear headings. Be concise but complete enough to revise from later. No MCQs."""

FLASHCARD_SYSTEM = """You create flashcards from study material.
Output a list of front/back pairs. Format each flashcard as:
Q: [Question or Concept]
A: [Answer or Definition]"""

QA_SYSTEM = """You are a helpful study assistant. 
Answer the user's question based strictly on the provided document text. 
Be clear, concise, and accurate."""


def read_pdf(path: str) -> str:
    doc = fitz.open(path)
    pages = []
    for i in tqdm(range(doc.page_count), desc="Reading PDF", unit="page"):
        pages.append(doc[i].get_text())
    doc.close()
    return "\n".join(pages).strip()


def ask_groq(client: Groq, system: str, user: str, desc: str) -> str:
    with tqdm(total=1, desc=desc, bar_format="{l_bar}{bar}| {elapsed}") as bar:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=TEMPERATURE,
        )
        bar.update(1)
    return response.choices[0].message.content or ""


def generate_mcqs(client: Groq, text: str) -> str:
    user = f"Create {MCQ_COUNT} multiple-choice questions from this text.\n\n{text}"
    return ask_groq(client, MCQ_SYSTEM, user, "Generating MCQs")


def generate_summary(client: Groq, text: str) -> str:
    user = f"Summarize this document.\n\n{text}"
    return ask_groq(client, SUMMARY_SYSTEM, user, "Generating summary")


def generate_revision(client: Groq, text: str) -> str:
    user = f"Create revision notes from this text.\n\n{text}"
    return ask_groq(client, REVISION_SYSTEM, user, "Generating revision notes")


def generate_flashcards(client: Groq, text: str) -> str:
    user = f"Create {FLASHCARD_COUNT} flashcards from this text.\n\n{text}"
    return ask_groq(client, FLASHCARD_SYSTEM, user, "Generating flashcards")


def split_mcq_output(raw: str) -> tuple[str, str]:
    marker_mcqs = "=== MCQS ==="
    marker_answers = "=== ANSWER KEY ==="

    if marker_mcqs not in raw or marker_answers not in raw:
        return raw.strip(), "(Could not split answer key — check model output.)"

    _, rest = raw.split(marker_mcqs, 1)
    mcqs_part, answers_part = rest.split(marker_answers, 1)
    return mcqs_part.strip(), answers_part.strip()


def main() -> None:
    if not GROQ_API_KEY:
        sys.exit("Set GROQ_API_KEY in your .env file.")
    if not os.path.isfile(PDF_PATH):
        sys.exit(f"PDF not found: {PDF_PATH}")

    text = read_pdf(PDF_PATH)
    if not text:
        sys.exit("No text found in PDF.")

    text = text[:MAX_TEXT_CHARS]
    client = Groq(api_key=GROQ_API_KEY)
    base = os.path.splitext(os.path.basename(PDF_PATH))[0]
    os.makedirs(OUT_DIR, exist_ok=True)

    raw_mcqs = generate_mcqs(client, text)
    mcqs, answers = split_mcq_output(raw_mcqs)
    summary = generate_summary(client, text)
    revision = generate_revision(client, text)
    flashcards = generate_flashcards(client, text)

    outputs = [
        (f"{base}_mcqs.txt", mcqs),
        (f"{base}_answer_key.txt", answers),
        (f"{base}_summary.txt", summary),
        (f"{base}_revision.txt", revision),
        (f"{base}_flashcard.txt", flashcards),
    ]

    for name, content in tqdm(outputs, desc="Writing files", unit="file"):
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        tqdm.write(f"Saved {path}")

    print("\n" + "="*40)
    print("Interactive Q&A Session")
    print("Type your question about the document below, or type 'quit' to exit.")
    print("="*40)
    
    while True:
        try:
            q = input("\nQuestion: ").strip()
            if q.lower() in ["quit", "exit", "q"]:
                print("Exiting Q&A. Goodbye!")
                break
            if not q:
                continue
                
            user_prompt = f"Based on the following text, answer the question.\n\nQuestion: {q}\n\nText:\n{text}"
            answer = ask_groq(client, QA_SYSTEM, user_prompt, "Fetching answer")
            print(f"\nAnswer:\n{answer}")
            
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Q&A. Goodbye!")
            break


if __name__ == "__main__":
    main()
