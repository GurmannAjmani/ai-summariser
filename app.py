import re
import fitz as _fitz
import streamlit as st
from groq import Groq
from main import (
    generate_mcqs,
    generate_summary,
    generate_revision,
    generate_flashcards,
    generate_diagrams,
    answer_question,
    split_mcq_output,
    render_mermaid_to_png,
    diagrams_to_pdf_bytes,
    GROQ_API_KEY,
    MAX_TEXT_CHARS,
)

st.set_page_config(page_title="AI Study Assistant", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background-color: #0e0e0e; color: #e0e0e0; }

    section[data-testid="stSidebar"] {
        background-color: #141414;
        border-right: 1px solid #2a2a2a;
    }

    h1, h2, h3, h4 { color: #ffffff; font-weight: 600; }

    .stButton > button {
        background-color: #1e1e1e;
        color: #ffffff;
        border: 1px solid #3a3a3a;
        border-radius: 6px;
        padding: 0.5rem 1.2rem;
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        transition: border-color 0.2s, background-color 0.2s;
    }
    .stButton > button:hover { background-color: #2a2a2a; border-color: #888; }

    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #1a1a1a;
        color: #e0e0e0;
        border: 1px solid #3a3a3a;
        border-radius: 6px;
        font-family: 'Inter', sans-serif;
    }

    .stFileUploader > div {
        background-color: #1a1a1a;
        border: 1px dashed #3a3a3a;
        border-radius: 6px;
    }

    .stTabs [data-baseweb="tab-list"] {
        background-color: #141414;
        border-bottom: 1px solid #2a2a2a;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #888;
        border: none;
        border-radius: 4px 4px 0 0;
        padding: 0.6rem 1.2rem;
        font-size: 0.875rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e1e1e;
        color: #ffffff;
        border-bottom: 2px solid #ffffff;
    }

    div[data-testid="stMarkdownContainer"] p { color: #c0c0c0; }

    .correct-answer {
        background-color: #1a2b1a;
        border: 1px solid #3a6b3a;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin-top: 0.5rem;
        color: #7dba7d;
    }
    .wrong-answer {
        background-color: #2b1a1a;
        border: 1px solid #6b3a3a;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin-top: 0.5rem;
        color: #ba7d7d;
    }
    .flashcard-front {
        background-color: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.5rem;
        font-weight: 500;
        color: #e0e0e0;
    }
    .flashcard-back {
        background-color: #141414;
        border: 1px solid #2a2a2a;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 1.25rem;
        color: #aaaaaa;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


def get_client() -> Groq | None:
    key = st.session_state.get("api_key", "") or GROQ_API_KEY
    return Groq(api_key=key) if key else None


def text_to_pdf_bytes(content: str) -> bytes:
    doc = _fitz.open()
    page = doc.new_page()
    page.insert_textbox(
        _fitz.Rect(50, 50, 562, 792),
        content,
        fontsize=11,
        fontname="helv",
        color=(0.9, 0.9, 0.9),
    )
    return doc.tobytes()


def get_pdf_text() -> str | None:
    if "pdf_text" in st.session_state:
        return st.session_state.pdf_text
    uploaded = st.session_state.get("uploaded_file")
    if not uploaded:
        return None
    doc = _fitz.open(stream=uploaded.read(), filetype="pdf")
    pages = [doc[i].get_text() for i in range(doc.page_count)]
    doc.close()
    text = "\n".join(pages).strip()[:MAX_TEXT_CHARS]
    st.session_state.pdf_text = text
    return text


def parse_mcqs(mcq_text: str) -> list[dict]:
    questions = []
    blocks = re.split(r'\n(?=\d+\.)', mcq_text.strip())
    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue
        q_text = lines[0]
        options = {}
        for line in lines[1:]:
            m = re.match(r'^([A-D])[).\s]\s*(.*)', line)
            if m:
                options[m.group(1)] = m.group(2).strip()
        if q_text and len(options) >= 2:
            questions.append({"question": q_text, "options": options})
    return questions


def parse_answer_key(answer_text: str) -> dict[int, str]:
    answers = {}
    for line in answer_text.splitlines():
        m = re.match(r'^(\d+)\.\s*([A-D])', line.strip())
        if m:
            answers[int(m.group(1))] = m.group(2)
    return answers


def parse_flashcards(raw: str) -> list[tuple[str, str]]:
    cards = []
    q = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("Q:"):
            q = line[2:].strip()
        elif line.startswith("A:") and q is not None:
            cards.append((q, line[2:].strip()))
            q = None
    return cards


def require_pdf_and_key() -> tuple[str | None, Groq | None]:
    client = get_client()
    if not client:
        st.error("Enter your Groq API key in the sidebar.")
        return None, None
    text = get_pdf_text()
    if not text:
        st.error("Upload a PDF in the sidebar first.")
        return None, None
    return text, client


# --- Sidebar ---
with st.sidebar:
    st.header("Setup")
    st.text_input("Groq API Key", type="password", value=GROQ_API_KEY, key="api_key")
    st.divider()
    st.header("Upload PDF")
    st.file_uploader("Choose a PDF", type=["pdf"], key="uploaded_file",
                     on_change=lambda: st.session_state.pop("pdf_text", None))
    st.divider()
    st.number_input("Number of MCQs", min_value=3, max_value=30, value=10, key="mcq_count")
    st.number_input("Number of Flashcards", min_value=3, max_value=30, value=10, key="flashcard_count")

# --- Main ---
st.title("AI Study Assistant")

tab_summary, tab_revision, tab_mcq, tab_flashcards, tab_diagrams, tab_qa = st.tabs([
    "Summary", "Revision Notes", "MCQ Quiz", "Flashcards", "Diagrams", "Q&A"
])

# --- Summary ---
with tab_summary:
    st.header("Summary")
    if st.button("Generate Summary", key="btn_summary"):
        text, client = require_pdf_and_key()
        if text and client:
            with st.spinner("Generating summary..."):
                st.session_state.summary = generate_summary(client, text)

    if "summary" in st.session_state:
        st.markdown(st.session_state.summary)
        st.download_button(
            label="Download as PDF",
            data=text_to_pdf_bytes(st.session_state.summary),
            file_name="summary.pdf",
            mime="application/pdf",
            key="dl_summary",
        )

# --- Revision ---
with tab_revision:
    st.header("Revision Notes")
    if st.button("Generate Revision Notes", key="btn_revision"):
        text, client = require_pdf_and_key()
        if text and client:
            with st.spinner("Generating revision notes..."):
                st.session_state.revision = generate_revision(client, text)

    if "revision" in st.session_state:
        st.markdown(st.session_state.revision)
        st.download_button(
            label="Download as PDF",
            data=text_to_pdf_bytes(st.session_state.revision),
            file_name="revision_notes.pdf",
            mime="application/pdf",
            key="dl_revision",
        )

# --- MCQ ---
with tab_mcq:
    st.header("MCQ Quiz")
    if st.button("Generate MCQs", key="btn_mcq"):
        text, client = require_pdf_and_key()
        if text and client:
            with st.spinner("Generating MCQs..."):
                raw = generate_mcqs(client, text, st.session_state.mcq_count)
                mcq_text, answer_text = split_mcq_output(raw)
                st.session_state.mcqs = parse_mcqs(mcq_text)
                st.session_state.answer_key = parse_answer_key(answer_text)
                st.session_state.user_answers = {}
                st.session_state.mcq_submitted = False

    if "mcqs" in st.session_state:
        questions = st.session_state.mcqs
        answer_key = st.session_state.answer_key

        if not questions:
            st.warning("Could not parse MCQs from the model output.")
        else:
            with st.form("mcq_form"):
                for i, q in enumerate(questions, 1):
                    st.markdown(f"**{i}. {q['question']}**")
                    options_list = [f"{k}) {v}" for k, v in q["options"].items()]
                    choice = st.radio(
                        label=f"q{i}",
                        options=options_list,
                        key=f"mcq_{i}",
                        label_visibility="collapsed"
                    )
                    st.session_state.user_answers[i] = choice[0] if choice else None
                    st.divider()
                if st.form_submit_button("Submit Answers"):
                    st.session_state.mcq_submitted = True

            if st.session_state.get("mcq_submitted"):
                correct = 0
                for i, q in enumerate(questions, 1):
                    user_ans = st.session_state.user_answers.get(i)
                    correct_ans = answer_key.get(i)
                    if user_ans and correct_ans:
                        if user_ans == correct_ans:
                            correct += 1
                            st.markdown(f'<div class="correct-answer">Q{i}: Correct — {correct_ans}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="wrong-answer">Q{i}: Wrong — You answered {user_ans}, correct is {correct_ans}</div>', unsafe_allow_html=True)
                st.markdown(f"### Score: {correct} / {len(questions)}")

# --- Flashcards ---
with tab_flashcards:
    st.header("Flashcards")
    if st.button("Generate Flashcards", key="btn_flashcards"):
        text, client = require_pdf_and_key()
        if text and client:
            with st.spinner("Generating flashcards..."):
                raw = generate_flashcards(client, text, st.session_state.flashcard_count)
                st.session_state.flashcards = parse_flashcards(raw)

    if "flashcards" in st.session_state:
        cards = st.session_state.flashcards
        if not cards:
            st.warning("Could not parse flashcards from the model output.")
        else:
            for i, (q, a) in enumerate(cards, 1):
                with st.expander(f"{i}. {q}"):
                    st.markdown(a)

# --- Diagrams ---
with tab_diagrams:
    st.header("Diagrams")
    if st.button("Generate Diagrams", key="btn_diagrams"):
        text, client = require_pdf_and_key()
        if text and client:
            with st.spinner("Generating and rendering diagrams..."):
                codes = generate_diagrams(client, text)
                pngs = [png for code in codes if (png := render_mermaid_to_png(code))]
                st.session_state.diagram_pngs = pngs
                st.session_state.diagram_pdf = diagrams_to_pdf_bytes(pngs) if pngs else None

    if "diagram_pngs" in st.session_state:
        pngs = st.session_state.diagram_pngs
        if not pngs:
            st.warning("No diagrams could be rendered. The Mermaid API may have rejected the generated code.")
        else:
            for i, png in enumerate(pngs, 1):
                st.markdown(f"**Diagram {i}**")
                st.image(png, width="stretch")
            if st.session_state.get("diagram_pdf"):
                st.download_button(
                    label="Download Diagrams as PDF",
                    data=st.session_state.diagram_pdf,
                    file_name="diagrams.pdf",
                    mime="application/pdf",
                )

# --- Q&A ---
with tab_qa:
    st.header("Q&A")
    question = st.text_input("Your question", placeholder="What is the main topic of this document?")
    if st.button("Ask", key="btn_ask"):
        if not question:
            st.warning("Please enter a question.")
        else:
            text, client = require_pdf_and_key()
            if text and client:
                with st.spinner("Thinking..."):
                    answer = answer_question(client, text, question)
                st.markdown("**Answer:**")
                st.markdown(answer)
