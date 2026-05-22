"""Read a PDF with PyMuPDF, generate study files with Groq."""

import os
import sys
import json
import urllib.request

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

DIAGRAM_SYSTEM = """You create helpful Mermaid.js diagrams to summarize study material.
Generate exactly 3 diagrams (like flowcharts, mindmaps, or graphs) based on the text.
Output ONLY the raw Mermaid code for each diagram, separated by this exact line:
=== DIAGRAM ===
CRITICAL: Do NOT output any explanations, titles, or markdown code blocks (```). Start directly with the graph type (e.g. 'graph TD'). Use valid Mermaid syntax only."""


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


def generate_diagrams(client: Groq, text: str) -> list[str]:
    user = f"Create 3 Mermaid diagrams summarizing this text.\n\n{text}"
    raw = ask_groq(client, DIAGRAM_SYSTEM, user, "Generating diagrams")
    # Clean up and split the raw text by the delimiter
    return [d.strip() for d in raw.split("=== DIAGRAM ===") if d.strip()]


def render_mermaid_to_png(mermaid_code: str) -> bytes | None:
    import base64
    
    # Clean up any residual markdown or explanations
    mermaid_code = mermaid_code.replace("```mermaid", "").replace("```", "").strip()
    
    # mermaid.ink requires base64 encoding
    encoded_str = base64.b64encode(mermaid_code.encode("utf-8")).decode("utf-8")
    url = f"https://mermaid.ink/img/{encoded_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-Summariser/1.0"
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception as e:
        tqdm.write(f"Error rendering diagram via mermaid.ink: {e}\nCode was:\n{mermaid_code}")
        return None


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

    diagram_codes = generate_diagrams(client, text)
    diagram_pdf_path = os.path.join(OUT_DIR, f"{base}_diagrams.pdf")
    pdf_doc = fitz.open()
    
    for i, code in enumerate(tqdm(diagram_codes, desc="Rendering diagrams", unit="diagram")):
        # Sometimes LLMs still wrap in markdown block, so we clean it
        code = code.replace("```mermaid", "").replace("```", "").strip()
        png_data = render_mermaid_to_png(code)
        if png_data:
            try:
                img_doc = fitz.open(stream=png_data, filetype="png")
                pdf_bytes = img_doc.convert_to_pdf()
                img_pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
                pdf_doc.insert_pdf(img_pdf)
                img_doc.close()
                img_pdf.close()
            except Exception as e:
                tqdm.write(f"Error inserting diagram {i+1} into PDF: {e}")
    
    if pdf_doc.page_count > 0:
        pdf_doc.save(diagram_pdf_path)
        tqdm.write(f"Saved {diagram_pdf_path}")
    pdf_doc.close()

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
