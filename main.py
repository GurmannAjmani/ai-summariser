import os
import base64
import urllib.request

import fitz
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
TEMPERATURE = 0.4
MAX_TEXT_CHARS = 120_000

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

MCQ_SYSTEM = """You create multiple-choice questions from study material.
Output exactly two sections with these headers on their own lines:

=== MCQS ===
(numbered questions, each with options A-D on separate lines)

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
Output a list of front/back pairs. Format each flashcard exactly as:
Q: [Question or Concept]
A: [Answer or Definition]"""

QA_SYSTEM = """You are a helpful study assistant.
Answer the user's question based strictly on the provided document text.
Be clear, concise, and accurate."""

DIAGRAM_SYSTEM = """You create helpful Mermaid.js diagrams to summarize study material.
Generate exactly 3 diagrams (like flowcharts, mindmaps, or graphs) based on the text.
Output ONLY the raw Mermaid code for each diagram, separated by this exact line:
=== DIAGRAM ===
CRITICAL: Do NOT output any explanations, titles, or markdown code blocks. Start directly with the graph type (e.g. 'graph TD'). Use valid Mermaid syntax only."""


def read_pdf(path: str) -> str:
    doc = fitz.open(path)
    pages = [doc[i].get_text() for i in range(doc.page_count)]
    doc.close()
    return "\n".join(pages).strip()


def ask_groq(client: Groq, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=TEMPERATURE,
    )
    return response.choices[0].message.content or ""


def generate_mcqs(client: Groq, text: str, count: int) -> str:
    return ask_groq(client, MCQ_SYSTEM, f"Create {count} multiple-choice questions from this text.\n\n{text}")


def generate_summary(client: Groq, text: str) -> str:
    return ask_groq(client, SUMMARY_SYSTEM, f"Summarize this document.\n\n{text}")


def generate_revision(client: Groq, text: str) -> str:
    return ask_groq(client, REVISION_SYSTEM, f"Create revision notes from this text.\n\n{text}")


def generate_flashcards(client: Groq, text: str, count: int) -> str:
    return ask_groq(client, FLASHCARD_SYSTEM, f"Create {count} flashcards from this text.\n\n{text}")


def generate_diagrams(client: Groq, text: str) -> list[str]:
    raw = ask_groq(client, DIAGRAM_SYSTEM, f"Create 3 Mermaid diagrams summarizing this text.\n\n{text}")
    return [d.strip() for d in raw.split("=== DIAGRAM ===") if d.strip()]


def answer_question(client: Groq, text: str, question: str) -> str:
    return ask_groq(client, QA_SYSTEM, f"Based on the following text, answer the question.\n\nQuestion: {question}\n\nText:\n{text}")


def split_mcq_output(raw: str) -> tuple[str, str]:
    marker_mcqs = "=== MCQS ==="
    marker_answers = "=== ANSWER KEY ==="
    if marker_mcqs not in raw or marker_answers not in raw:
        return raw.strip(), ""
    _, rest = raw.split(marker_mcqs, 1)
    mcqs_part, answers_part = rest.split(marker_answers, 1)
    return mcqs_part.strip(), answers_part.strip()


def render_mermaid_to_png(mermaid_code: str) -> bytes | None:
    mermaid_code = mermaid_code.replace("```mermaid", "").replace("```", "").strip()
    encoded_str = base64.b64encode(mermaid_code.encode("utf-8")).decode("utf-8")
    url = f"https://mermaid.ink/img/{encoded_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AI-Summariser/1.0"})
    try:
        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception:
        return None


def diagrams_to_pdf_bytes(png_images: list[bytes]) -> bytes | None:
    pdf_doc = fitz.open()
    for png_data in png_images:
        try:
            img_doc = fitz.open(stream=png_data, filetype="png")
            pdf_bytes = img_doc.convert_to_pdf()
            img_pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
            pdf_doc.insert_pdf(img_pdf)
            img_doc.close()
            img_pdf.close()
        except Exception:
            continue
    if pdf_doc.page_count > 0:
        return pdf_doc.tobytes()
    return None
