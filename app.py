from flask import Flask, request, render_template, session
import uuid
import PyPDF2
import os
import hashlib
from dotenv import load_dotenv
from groq import Groq
from supabase import create_client

# =========================
# 🔑 LOAD ENV
# =========================

load_dotenv()

app = Flask(__name__)
app.secret_key = "brainboost-secret-key"

# =========================
# 🔑 API CONFIG
# =========================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

client = Groq(api_key=GROQ_API_KEY)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

MODEL_ID = "llama-3.1-8b-instant"

# =========================
# 📊 TOKEN TRACKING
# =========================

DAILY_TOKEN_LIMIT = 500000

def get_total_used(user_id):

    result = supabase.table("token_usage") \
        .select("total_tokens") \
        .eq("user_id", user_id) \
        .execute()

    if result.data:
        return result.data[0]["total_tokens"]

    return 0


def update_usage(user_id, tokens):

    current_total = get_total_used(user_id)

    new_total = current_total + tokens

    existing = supabase.table("token_usage") \
        .select("id") \
        .eq("user_id", user_id) \
        .execute()

    if existing.data:

        supabase.table("token_usage").update({
            "total_tokens": new_total
        }).eq("user_id", user_id).execute()

    else:

        supabase.table("token_usage").insert({
            "user_id": user_id,
            "total_tokens": new_total
        }).execute()

    return new_total


# =========================
# 📄 EXTRACT TEXT
# =========================

def extract_text(file):

    text = ""

    try:

        if file.filename.endswith(".txt"):
            text = file.read().decode("utf-8")

        elif file.filename.endswith(".pdf"):

            reader = PyPDF2.PdfReader(file)

            for page in reader.pages:

                extracted = page.extract_text()

                if extracted:
                    text += extracted + "\n"

    except Exception as e:
        print("❌ File Error:", e)

    return text.strip()


# =========================
# 🔑 GENERATE HASH
# =========================

def generate_hash(text):

    return hashlib.md5(text.encode()).hexdigest()


# =========================
# 🤖 GROQ REQUEST
# =========================

def ask_groq(prompt, tokens=1000):

    try:

        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert academic tutor."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=tokens
        )

        return {
            "content": completion.choices[0].message.content,
            "tokens": completion.usage.total_tokens
        }

    except Exception as e:

        print("❌ Groq Error:", e)

        return {
            "content": f"⚠️ AI Error: {e}",
            "tokens": 0
        }


# =========================
# 🏠 MAIN ROUTE
# =========================

@app.route("/", methods=["GET", "POST"])
def index():

    # =========================
    # 👤 USER SESSION
    # =========================

    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

    user_id = session["user_id"]

    notes_part = ""
    flashcards_part = ""
    map_part = ""
    full_content = ""

    last_request_tokens = 0

    total_used_today = get_total_used(user_id)

    if request.method == "POST":

        mode = request.form.get("mode")
        file = request.files.get("file")

        # =========================
        # 📥 INPUT
        # =========================

        if file and file.filename != "":
            text = extract_text(file)

        else:
            text = request.form.get("notes", "")

        full_content = text

        if not text.strip():

            return render_template(
                "index.html",
                notes_part="⚠️ Please provide text."
            )

        # 🔥 limit for speed
        process_text = text[:8000]

        # =========================
        # 🔑 HASH
        # =========================

        note_hash = generate_hash(process_text)

        # =====================================================
        # 📄 SUMMARY
        # =====================================================

        if mode == "notes":

            summary_check = supabase.table("notes") \
                .select("summary") \
                .eq("note_hash", note_hash) \
                .execute()

            if (
                summary_check.data and
                summary_check.data[0]["summary"]
            ):

                print("⚡ Loaded summary from cache")

                notes_part = summary_check.data[0]["summary"]

            else:

                prompt = f"""
You are a Senior Academic Researcher.

Create a HIGH-QUALITY structured summary.

STRUCTURE:
1. Core Idea
2. Key Concepts
3. Technical Explanation
4. Relationships Between Concepts

RULES:
- Detailed but concise
- Professional tone
- Use headings
- Use bullet points

TEXT:
{process_text}
"""

                result = ask_groq(prompt, tokens=1200)

                notes_part = result["content"]

                last_request_tokens = result["tokens"]

                existing = supabase.table("notes") \
                    .select("id") \
                    .eq("note_hash", note_hash) \
                    .execute()

                if existing.data:

                    supabase.table("notes").update({
                        "summary": notes_part
                    }).eq("note_hash", note_hash).execute()

                else:

                    supabase.table("notes").insert({
                        "note_hash": note_hash,
                        "title": file.filename if file else "Manual Notes",
                        "content": process_text,
                        "summary": notes_part
                    }).execute()

                print("✅ Summary saved")

        # =====================================================
        # 🧠 FLASHCARDS
        # =====================================================

        elif mode == "flashcards":

            flashcard_check = supabase.table("notes") \
                .select("flashcards") \
                .eq("note_hash", note_hash) \
                .execute()

            if (
                flashcard_check.data and
                flashcard_check.data[0]["flashcards"]
            ):

                print("⚡ Loaded flashcards from cache")

                flashcards_part = flashcard_check.data[0]["flashcards"]

            else:

                prompt = f"""
You are an expert professor.

Generate HIGH-QUALITY flashcards.

RULES:
- Cover ALL important concepts
- No repeated questions
- Questions must be meaningful
- Answers must be 2–3 sentences

FORMAT:
Q: ...
A: ...

TEXT:
{process_text}
"""

                result = ask_groq(prompt, tokens=1400)

                flashcards_part = result["content"]

                last_request_tokens = result["tokens"]

                existing = supabase.table("notes") \
                    .select("id") \
                    .eq("note_hash", note_hash) \
                    .execute()

                if existing.data:

                    supabase.table("notes").update({
                        "flashcards": flashcards_part
                    }).eq("note_hash", note_hash).execute()

                else:

                    supabase.table("notes").insert({
                        "note_hash": note_hash,
                        "title": file.filename if file else "Manual Notes",
                        "content": process_text,
                        "flashcards": flashcards_part
                    }).execute()

                print("✅ Flashcards saved")

        # =====================================================
        # 🗺️ MIND MAP
        # =====================================================

        elif mode == "map":

            map_check = supabase.table("notes") \
                .select("mindmap") \
                .eq("note_hash", note_hash) \
                .execute()

            if (
                map_check.data and
                map_check.data[0]["mindmap"]
            ):

                print("⚡ Loaded mindmap from cache")

                map_part = map_check.data[0]["mindmap"]

            else:

                prompt = f"""
Create a concise hierarchical mind map.

STRICT RULES:
- ONLY plain text
- NO markdown
- NO bullets
- NO numbering
- EXACTLY 2 spaces indentation
- Maximum 1-3 words per node
- Maximum 3 levels

EXAMPLE:

Computer
  Hardware
    CPU
    RAM
  Software
    OS
    Apps

TEXT:
{process_text}
"""

                result = ask_groq(prompt, tokens=700)

                map_part = result["content"]

                last_request_tokens = result["tokens"]

                existing = supabase.table("notes") \
                    .select("id") \
                    .eq("note_hash", note_hash) \
                    .execute()

                if existing.data:

                    supabase.table("notes").update({
                        "mindmap": map_part
                    }).eq("note_hash", note_hash).execute()

                else:

                    supabase.table("notes").insert({
                        "note_hash": note_hash,
                        "title": file.filename if file else "Manual Notes",
                        "content": process_text,
                        "mindmap": map_part
                    }).execute()

                print("✅ Mindmap saved")

        # =========================
        # 📊 UPDATE TOKENS
        # =========================

        total_used_today = update_usage(
            user_id,
            last_request_tokens
        )

    tokens_remaining = DAILY_TOKEN_LIMIT - total_used_today

    return render_template(
        "index.html",
        notes_part=notes_part,
        flashcards_part=flashcards_part,
        map_part=map_part,
        full_content=full_content,
        last_request_tokens=last_request_tokens,
        tokens_remaining=tokens_remaining
    )


# =========================
# 🚀 RUN
# =========================

if __name__ == "__main__":
    app.run(debug=True)