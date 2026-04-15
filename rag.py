import json
import os
import re

import requests
from dotenv import load_dotenv
from groq import Groq
from qdrant_client import QdrantClient

from swedish_tax_calculator import calculate_tax, detect_calculation_request
from swedish_tax_facts_2026 import QUICK_ANSWERS, calculate_reseavdrag

load_dotenv()

MODEL_NAME = "qwen3.5:27b"

HF_EMBED_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    "mixedbread-ai/mxbai-embed-large-v1/pipeline/feature-extraction"
)

PROMPT_TEMPLATE = """You are a precise Swedish tax assistant.

STRICT RULES — follow these exactly:
1. ONLY use information from the context provided below
2. If context does not contain the answer, say:
   "Jag hittar inte den informationen i dokumenten.
    Kontakta Skatteverket på skatteverket.se för korrekt svar."
3. NEVER invent tax rates, percentages or kronor amounts
4. NEVER use tax rules from other years than 2026
5. If asked about a specific municipality rate, say you don't know
   unless the context mentions it (the calculator handles rates)
6. Answer in the SAME language as the question
7. Keep answers concise and factual

Context from official Skatteverket documents:
{context}

Question: {question}

Answer (be precise, cite document when possible):"""

FALLBACK_PROMPT_TEMPLATE = """You are a helpful Swedish tax assistant.
Answer this question about Swedish tax from your knowledge.
Be helpful, accurate and answer in the same language as the question.

Question: {question}

Answer:"""


# ── Embeddings ────────────────────────────────────────────────────────────────

def get_embeddings_hf(texts: list) -> list:
    headers = {"Authorization": f"Bearer {os.getenv('HF_API_KEY')}"}
    response = requests.post(HF_EMBED_URL, headers=headers, json={"inputs": texts})
    response.raise_for_status()
    return response.json()


def get_single_embedding(text: str) -> list:
    return get_embeddings_hf([text])[0]


# ── Retrieval ─────────────────────────────────────────────────────────────────

def search_qdrant(question: str, limit: int = 5) -> list[dict]:
    """Return a list of payload dicts from the top matching Qdrant points."""
    embedding = get_single_embedding(question)

    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

    results = client.query_points(
        collection_name="swedish_tax",
        query=embedding,
        limit=limit,
    ).points

    return [r.payload for r in results]


def clean_payloads(results: list) -> list:
    cleaned = []
    for r in results:
        text = (
            r.get("document") or
            r.get("page_content") or
            r.get("text") or
            ""
        )

        if len(text.strip()) < 150:
            continue
        letters = sum(c.isalpha() for c in text)
        if letters / len(text) < 0.50:
            continue
        if text.count('.') < 2:
            continue
        digits = sum(c.isdigit() for c in text)
        if digits / len(text) > 0.30:
            continue
        cleaned.append(r)

    return cleaned


def has_good_chunks(payloads: list[dict]) -> bool:
    """True if at least 3 payloads pass the letter_ratio quality bar."""
    if len(payloads) < 3:
        return False
    good = sum(
        1 for p in payloads
        if (text := (p.get("document") or p.get("page_content") or ""))
        and sum(c.isalpha() for c in text) / len(text) > 0.5
    )
    return good >= 3


def calculate_confidence(docs: list) -> str:
    """Rate how confident we are in the answer."""

    if not docs:
        return "low"

    # Count how many chunks have good letter ratio
    good_chunks = sum(
        1 for d in docs
        if (text := d.get("document") or d.get("page_content") or d.get("text") or "")
        and sum(c.isalpha() for c in text) / max(len(text), 1) > 0.5
    )

    if good_chunks >= 3:
        return "high"
    elif good_chunks >= 1:
        return "medium"
    else:
        return "low"


# ── Disclaimer ───────────────────────────────────────────────────────────────

def add_disclaimer(answer: str, question: str) -> str:
    tax_keywords = [
        "procent", "percent", "%", "kr", "sek",
        "avdrag", "skatt", "tax", "deduction",
    ]

    has_numbers = any(k in answer.lower() for k in tax_keywords)

    if has_numbers:
        disclaimer = "\n\n---\n⚠️ *Always verify with Skatteverket.se or a licensed tax advisor for your specific situation.*"
        return answer + disclaimer

    return answer


# ── Hallucination check ───────────────────────────────────────────────────────

def check_for_hallucination(answer: str) -> tuple[str, bool]:
    """Detect common hallucination patterns and flag them."""

    hallucination_flags = [
        # Wrong state tax rates (Sweden only has 20%)
        r"21\.3%", r"22\.6%", r"25%.*state tax",
        # Wrong thresholds (common hallucination)
        r"548[\s,]780", r"SEK 614,000.*state",
        # Invented rules
        r"as of 2023.*tax rate",
        r"2024.*21\.3",
    ]

    flagged = False
    for pattern in hallucination_flags:
        if re.search(pattern, answer, re.IGNORECASE):
            flagged = True
            break

    if flagged:
        warning = "⚠️ Note: Some figures in this answer may be outdated. "
        warning += "Please verify current rates at skatteverket.se\n\n"
        return warning + answer, True

    return answer, False


# ── Quick answers ─────────────────────────────────────────────────────────────

def check_quick_answer(question: str) -> str | None:
    q_lower = question.lower()
    for keyword, answer in QUICK_ANSWERS.items():
        if keyword in q_lower:
            return answer
    return None


# ── LLM ──────────────────────────────────────────────────────────────────────

def strip_think_tags(text: str) -> str:
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def call_qwen(prompt: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 1024, "num_ctx": 4096},
            "think": False,
        },
        timeout=300,
    )
    data = response.json()
    return strip_think_tags(data.get("response", ""))


def call_groq(prompt: str, history: list | None = None) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    messages = []
    for msg in (history or [])[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "qwen/qwen3-32b"),
        messages=messages,
        temperature=0.1,
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()


def call_llm(prompt: str, history: list | None = None) -> str:
    if os.getenv("USE_GROQ") == "true":
        return call_groq(prompt, history)
    return call_qwen(prompt)


def search_and_answer(question: str) -> str:
    """Use Groq with web search tool for real-time verified answers."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # supports web search
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise Swedish tax assistant. "
                    "Search for current, accurate Swedish tax information. "
                    "Always cite your sources. "
                    "Answer in the same language as the question. "
                    "Only state verified facts — never guess. "
                    "Always recommend Skatteverket.se for official guidance."
                ),
            },
            {
                "role": "user",
                "content": f"{question}\n\nSearch for the most current Swedish tax rules from Skatteverket.se",
            },
        ],
        tools=[{"type": "web_search_preview"}],
        tool_choice="auto",
        max_tokens=1024,
    )

    return response.choices[0].message.content or ""


# ── Follow-up questions ───────────────────────────────────────────────────────

def generate_followups(question: str, answer: str) -> list:
    """Generate 3 relevant follow-up questions."""
    try:
        followup_prompt = f"""Based on this Swedish tax question and answer, suggest 3 short follow-up questions.
Return ONLY a valid JSON array of 3 strings. No explanation, no markdown, just the array.
Example: ["How do I file this?", "What is the deadline?", "Can I deduct more?"]

Question: {question}
Answer: {answer[:300]}

JSON array:"""

        response = call_groq(followup_prompt)
        response = response.strip()
        match = re.search(r'\[.*?\]', response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"Followup generation failed: {e}")
    return []


# ── Main entry point ──────────────────────────────────────────────────────────

def ask_question(question: str, history: list | None = None) -> dict:
    # ── Extract profile data embedded in the question string ──────────────────
    profile_salary = None
    profile_kommun = None

    salary_match = re.search(
        r'Annual salary[:\s]+(\d[\d\s,\.]+)\s*kr',
        question,
        re.IGNORECASE,
    )
    if salary_match:
        raw = salary_match.group(1).replace(',', '').replace(' ', '').replace('.', '')
        try:
            profile_salary = float(raw)
            print(f"Profile salary detected: {profile_salary}")
        except Exception:
            pass

    kommun_match = re.search(
        r'Municipality[:\s]+([^\n,\]]+)',
        question,
        re.IGNORECASE,
    )
    if kommun_match:
        profile_kommun = kommun_match.group(1).strip().lower()
        print(f"Profile kommun detected: {profile_kommun}")

    # ── Tax calculator path ───────────────────────────────────────────────────
    calc = detect_calculation_request(question)

    # Fill in missing salary/kommun from profile if the question didn't supply them
    if not calc["salary"] and profile_salary:
        calc["salary"] = profile_salary
        calc["needs_calculation"] = True

    if not calc["kommun"] and profile_kommun:
        calc["kommun"] = profile_kommun

    # Trigger calculator for "what's my tax" questions when profile has a salary
    tax_trigger_words = [
        "what's my tax", "my tax", "min skatt", "vad betalar jag",
        "hur mycket skatt", "calculate my", "räkna min",
    ]
    if any(t in question.lower() for t in tax_trigger_words) and profile_salary:
        calc["needs_calculation"] = True
        calc["salary"] = calc["salary"] or profile_salary
        calc["kommun"] = calc["kommun"] or profile_kommun or "sverige"

    if calc["needs_calculation"] and calc["salary"]:
        result = calculate_tax(calc["salary"], calc["kommun"])

        calc_context = f"""
TAX CALCULATION — {result['kommun']} 2026

━━━ BOTTOM LINE (most important) ━━━
💰 NET salary per MONTH:  {result['net_salary_month']:,.0f} kr
💰 NET salary per YEAR:   {result['net_salary_year']:,.0f} kr
📊 Effective tax rate:    {result['effective_rate']}%
📊 Total tax per year:    {result['total_tax']:,.0f} kr

━━━ FULL BREAKDOWN ━━━
Gross salary:             {result['salary']:,.0f} kr/year
Basic deduction:        - {result['grundavdrag']:,.0f} kr (grundavdrag — standard yearly deduction)
Taxable income:           {result['taxable_income']:,.0f} kr
Municipal tax {result['kommunal_rate']}%:     - {result['kommunal_skatt']:,.0f} kr/year
State tax 20%:          - {result['statlig_skatt']:,.0f} kr/year
Job tax credit:         + {result['jobbskatteavdrag']:,.0f} kr/year (jobbskatteavdrag)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL TAX:                {result['total_tax']:,.0f} kr/year

Data: SCB official 2026 rates + Skatteverket rules
"""

        prompt = f"""You are a Swedish tax assistant.
The user asked: {question}

Here is the precise tax calculation:
{calc_context}

Lead with the net monthly salary as the FIRST thing you say.
Then explain the breakdown.
Make it very clear what is yearly vs monthly.
Explain what each component means in plain language.
Answer in the same language as the question.
Do NOT make up any numbers — use ONLY the figures above."""

        answer = call_llm(prompt, history)
        answer = strip_think_tags(answer)
        answer, was_flagged = check_for_hallucination(answer)
        followups = generate_followups(question, answer)

        return {
            "answer": answer,
            "sources": [{
                "filename": f"SCB Official Municipality Tax Rates 2026 — {result['kommun']}",
                "page": 0,
                "snippet": f"Municipal tax rate: {result['kommunal_rate']}% | Net salary: {result['net_salary_month']:,.0f} kr/month",
            }],
            "confidence": "high",
            "hallucination_flagged": was_flagged,
            "search_used": False,
            "followups": followups,
            "calculation": result,
        }

    # ── Reseavdrag calculator path ────────────────────────────────────────────
    reseavdrag_match = re.search(
        r'(\d+)\s*(?:km|kilometer|mil).*?(\d+)\s*(?:days|dagar|dag)',
        question, re.IGNORECASE
    )
    if not reseavdrag_match:
        reseavdrag_match = re.search(
            r'(\d+)\s*(?:days|dagar).*?(\d+)\s*(?:km|kilometer)',
            question, re.IGNORECASE
        )

    if reseavdrag_match and any(w in question.lower() for w in
            ['travel', 'commute', 'resa', 'pendla', 'reseavdrag', 'km', 'deduct']):

        km_match = re.search(r'(\d+)\s*km', question, re.IGNORECASE)
        days_match = re.search(r'(\d+)\s*(?:days|dagar)', question, re.IGNORECASE)

        if km_match and days_match:
            km = float(km_match.group(1))
            days = int(days_match.group(1))

            result = calculate_reseavdrag(km, days)

            reseavdrag_context = f"""
RESEAVDRAG CALCULATION 2026 (Skatteverket official rates):

Travel details:
- One way distance: {result['km_one_way']} km
- Work days per year: {result['work_days']} days
- Total km per year: {result['total_km_year']} km

Cost calculation:
- Rate: {result['rate_per_km']} kr/km (25 kr/mil — Skatteverket 2026)
- Total commute cost: {result['total_cost']:,.0f} kr/year
- Threshold (beloppsgräns): {result['threshold']:,.0f} kr

Result:
- Deductible amount: {result['deductible_amount']:,.0f} kr
- Estimated tax saving: ~{result['estimated_tax_saving']:,.0f} kr/year
- Qualifies for deduction: {'YES ✅' if result['qualifies'] else 'NO ❌ (below threshold)'}

Requirements to qualify:
1. Minimum 5 km one way ✅
2. Must save 2+ hours/day vs public transport
3. Costs must exceed {result['threshold']:,.0f} kr/year threshold
"""

            prompt = f"""You are a Swedish tax assistant.
{reseavdrag_context}

User question: {question}

Explain the reseavdrag calculation clearly.
State if they qualify and how much they save.
Mention the requirements they need to check.
Answer in the same language as the question."""

            answer = call_llm(prompt, history)
            answer = strip_think_tags(answer)
            followups = generate_followups(question, answer)

            return {
                "answer": answer,
                "sources": [{
                    "filename": "Skatteverket Reseavdrag 2026 — Official Rates",
                    "page": 0,
                    "snippet": f"Rate: 25 kr/mil | Threshold: {result['threshold']:,.0f} kr | Deductible: {result['deductible_amount']:,.0f} kr",
                }],
                "confidence": "high",
                "hallucination_flagged": False,
                "search_used": False,
                "followups": followups,
            }

    # ── RAG path ──────────────────────────────────────────────────────────────
    quick = check_quick_answer(question)
    verified_context = f"VERIFIED FACT: {quick}\n\n" if quick else ""

    payloads = clean_payloads(search_qdrant(question, limit=5))
    confidence = calculate_confidence(payloads)

    if has_good_chunks(payloads):
        print(f"RAG path — {len(payloads)} good chunks found")
        context = verified_context + "\n\n".join(
            p.get("document") or p.get("page_content") or p.get("text") or ""
            for p in payloads
        )
        prompt = PROMPT_TEMPLATE.format(context=context, question=question)

        if confidence == "low":
            # Try web search for a better answer before falling back to weak RAG
            try:
                web_answer = strip_think_tags(search_and_answer(question))
                if web_answer and len(web_answer) > 100:
                    return {
                        "answer": web_answer,
                        "sources": [{
                            "filename": "Web Search — Live Skatteverket Data",
                            "page": 0,
                            "snippet": "Answer sourced from real-time web search",
                        }],
                        "confidence": "web",
                        "hallucination_flagged": False,
                        "search_used": True,
                        "followups": generate_followups(question, web_answer),
                    }
            except Exception as e:
                print(f"Web search failed: {e}")
            # Web search failed or returned nothing — continue with low-confidence prompt hint
            prompt += """
    IMPORTANT: The documents do not contain clear information
    about this topic. Say so clearly at the start of your answer.
    Do NOT invent tax rates, rules or numbers.
    Only state what you know for certain from general knowledge.
    Always recommend the user verify with Skatteverket.
    """
        elif confidence == "medium":
            prompt += """
    The documents have partial information.
    Be careful to only state what is clearly in the context.
    Flag any uncertainty explicitly.
    """

        print("Context length:", len(context))
        print("Prompt being sent:", prompt[:500])

        answer = call_llm(prompt, history)
        print("Cleaned answer:", repr(answer[:200]))

        if not answer:
            answer = "Kunde inte generera svar. Försök igen."

        search_used = False
        sources = []
        for p in payloads:
            text = p.get("document") or p.get("page_content") or p.get("text") or ""
            sources.append({
                "page": p.get("page", 0),
                "snippet": text[:200],
                "filename": p.get("source") or p.get("filename") or "",
            })

        if not answer or "hittar inte" in answer.lower() or len(answer) < 50:
            try:
                web_answer = search_and_answer(question)
                if web_answer and len(web_answer) > 100:
                    answer = web_answer
                    sources.append({
                        "filename": "Web Search Fallback",
                        "page": 0,
                        "snippet": "RAG found no good answer — web search used",
                    })
                    search_used = True
            except Exception:
                pass

        answer, was_flagged = check_for_hallucination(answer)
        answer = add_disclaimer(answer, question)

        return {
            "answer": answer,
            "confidence": confidence,
            "hallucination_flagged": was_flagged,
            "search_used": search_used,
            "sources": sources,
            "followups": generate_followups(question, answer),
        }

    else:
        print(f"Fallback path — only {len(payloads)} usable chunks, answering from model knowledge")
        prompt = verified_context + FALLBACK_PROMPT_TEMPLATE.format(question=question)

        answer = call_llm(prompt, history)
        print("Fallback answer:", repr(answer[:200]))

        if not answer:
            answer = "Kunde inte generera svar. Försök igen."

        answer += "\n\n*(Svar baserat på allmän kunskap, ej från dina dokument)*"
        answer, was_flagged = check_for_hallucination(answer)
        answer = add_disclaimer(answer, question)

        return {
            "answer": answer,
            "confidence": confidence,
            "hallucination_flagged": was_flagged,
            "search_used": False,
            "sources": [],
            "followups": generate_followups(question, answer),
        }


if __name__ == "__main__":
    result = ask_question("Vad är F-skatt?")
    print("Svar:", result["answer"])
    print("\nKällor:")
    for s in result["sources"]:
        print(f"  - {s['filename']} (sida {s['page']}): {s['snippet'][:100]}...")
