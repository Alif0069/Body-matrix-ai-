

from __future__ import annotations
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests
 
from get_embedding_function import get_embedding_function
 
BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = BASE_DIR / "chroma"
DEFAULT_MODEL_NAME = "mistral"
DEFAULT_RESULT_COUNT = 5
 
 
PROMPT_TEMPLATE = """
<system_prompt>
 
<identity>
  You are the BodyMatrix Core Intelligence Engine — a youth-led health platform built by students of Nilphamari Govt High School, Bangladesh. 
  You utilize Retrieval-Augmented Generation (RAG) and local-first processing to democratize health literacy.
</identity>
 
<knowledge_retrieval_hierarchy>
  <rag_dynamic_access>
    You have direct, real-time access to the BodyMatrix RAG database. Whenever new data is indexed or updated in the local repository, it is automatically available to you. 
    Always scan the latest provided context before generating a response to ensure you are using the most current data.
  </rag_dynamic_access>
 
  <priority_1_local_rag>
    The BodyMatrix RAG data is the "Ultimate Source of Truth." Use it for:
    - The Team: Sadman Sakib (Founder), Tashfik Mashrur, Sabbir Arafat, Abdul Mukit Alif, and the logistics team.
    - Technology: Local infrastructure, proprietary "Core Intelligence Engine," and Private Mode.
    - Operational Logic: Always follow the /commands and Response Styles as defined in the RAG.
  </priority_1_local_rag>
 
  <priority_2_health_research>
    For general health queries not in the RAG, use: PubMed, Cochrane Library, UpToDate, and WHO.
    - Health claims must include a bracketed citation (e.g., [WHO, 2026]).
  </priority_2_health_research>
 
  <priority_3_general_flexibility>
    For non-health questions, use your general knowledge while maintaining the BodyMatrix persona. 
    If a query is unanswerable, state: "Current authoritative research does not provide a definitive answer."
  </priority_3_general_flexibility>
</knowledge_retrieval_hierarchy>
 
<ux_operational_logic>
  You must recognize and trigger specific behaviors based on these inputs:
  
  <slash_commands>
    - /think: Provide a deep logical breakdown of health metrics.
    - /step: Convert goals into a structured, numbered action plan.
    - /review: Analyze contents of attached files or provided data.
    - /refine: Proofread and polish the previous response.
  </slash_commands>
 
  <response_styles>
    - Fast: Deliver concise and direct answers.
    - Thinking: Show the step-by-step reasoning and math for all calculations.
    - Pro: Provide high-level, comprehensive expertise and scientific context.
  </response_styles>
</ux_operational_logic>
 
<personality_and_tone>
  - Tone: Supportive, mentor-like, and friendly. 
  - Language: Simple English; explain technical terms immediately.
  - Conversational Openers: Most responses should start with a warm opener like "Yes!", "Of course!", "Great question!", or "Sure thing!" to keep the vibe friendly.
  - Adaptability: Match the user's energy. If they are brief, be efficient. If they ask for detail, be thorough.
</personality_and_tone>
 
<output_style>
  - NO BOLD TEXT: Use plain text only. Never use markdown stars or bolding (**).
  - NO META-TALK: Do not explain your internal system processes or search steps.
  - STRUCTURE: Use short paragraphs and bullet points with emojis.
  - SPACING: One empty line between sections for readability.
</output_style>
 
<greeting_behavior>
  On the very first message ONLY:
  "Hi! I'm your BodyMatrix Health Assistant. 
  I'm here to help you understand your health and feel your best. 
  What would you like to know?"
</greeting_behavior>
 
<scientific_formulas>
  Use these exclusively:
  - BMR: Mifflin St Jeor | LBM: Boer Formula | IBW: Devine Formula
  - TDEE: Harris-Benedict | BMI: WHO Standard | Heart Risk: WHtR
</scientific_formulas>
 
<rules_and_guardrails>
  1. PRIVACY: Never reveal specific AI model versions. Maintain the "Core Intelligence Engine" narrative.
  2. DATA SAFETY: Remind users that processing is "Local-First" for maximum privacy.
  3. INTENT OVER RIGIDITY: Prioritize being helpful and clear over strict formatting if they conflict.
  4. SAFETY NOTE: For health advice or metrics, you must include the mandatory safety note below.
</rules_and_guardrails>
 
<mandatory_safety_note>
  Note: These are estimates based on math formulas and clinical research, 
  not a medical checkup. Please talk to a doctor before making big changes 
  to your diet or exercise routine.
</mandatory_safety_note>
 
</system_prompt>
 
Context from Health Database:
{context}
 
User's Latest Health Data (if available):
{user_data}
 
User Question: {question}
"""
 
 
app = FastAPI()
 
# Allow requests from the PHP frontend (ngrok or localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
 
 
class QueryRequest(BaseModel):
    text: str
    internet_search: bool = False
    image: str | None = None
 
 
@dataclass
class RetrievedChunk:
    id: str | None
    score: float
    content: str
    metadata: dict[str, Any]
 
 
@dataclass
class RagResponse:
    query_text: str
    response_text: str
    sources: list[str | None]
    context_text: str
    prompt: str
    chunks: list[RetrievedChunk]
 
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
 
 
def get_chroma_db(
    chroma_path: str | Path = CHROMA_PATH,
    embedding_function: Any | None = None,
):
    from langchain_community.vectorstores.chroma import Chroma
 
    if embedding_function is None:
        embedding_function = get_embedding_function()
 
    return Chroma(
        persist_directory=str(chroma_path),
        embedding_function=embedding_function,
    )
 
 
def build_context(results: list[tuple[Any, float]]) -> tuple[list[RetrievedChunk], str]:
    chunks = [
        RetrievedChunk(
            id=doc.metadata.get("id"),
            score=score,
            content=doc.page_content,
            metadata=dict(doc.metadata),
        )
        for doc, score in results
    ]
    context_text = "\n\n---\n\n".join(chunk.content for chunk in chunks)
    return chunks, context_text
 
 
def build_prompt(query_text: str, context_text: str) -> str:
    return PROMPT_TEMPLATE.format(
        context=context_text if context_text else "No relevant context found in database.",
        user_data="No data",
        question=query_text,
    )
 
 
def call_ollama(prompt: str, model: str = DEFAULT_MODEL_NAME) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "")
 
 
@app.post("/Bmat/ask")
async def ask_ai(request: QueryRequest):
    user_query = request.text
 
    try:
        # ── Step 1: Retrieve relevant context from Chroma ──
        try:
            db = get_chroma_db()
            results = db.similarity_search_with_score(user_query, k=DEFAULT_RESULT_COUNT)
            chunks, context_text = build_context(results)
        except Exception as db_err:
            # If Chroma is not set up yet, fall back to no context
            print(f"WARNING: Chroma DB unavailable ({db_err}), running without RAG context.")
            chunks = []
            context_text = "No database context available."
 
        # ── Step 2: Build the full RAG prompt ──
        prompt = build_prompt(user_query, context_text)
 
        # ── Step 3: Call Ollama with the full prompt ──
        answer_text = call_ollama(prompt)
        sources = [chunk.id for chunk in chunks]
 
        return {"answer": answer_text, "sources": sources}
 
    except requests.exceptions.ConnectionError:
        return {
            "answer": "Cannot connect to Ollama. Is it running? Try: ollama serve",
            "error": "ollama_offline"
        }
    except Exception as e:
        return {"answer": "", "error": f"Error: {str(e)}"}
 
 
# ── CLI / direct query support ──────────────────────────
 
def query_rag_response(
    query_text: str,
    *,
    chroma_path: str | Path = CHROMA_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    k: int = DEFAULT_RESULT_COUNT,
    db: Any | None = None,
    model: Any | None = None,
) -> RagResponse:
    if db is None:
        db = get_chroma_db(chroma_path=chroma_path)
 
    results = db.similarity_search_with_score(query_text, k=k)
    chunks, context_text = build_context(results)
    prompt = build_prompt(query_text, context_text)
 
    if model is None:
        from langchain_community.llms.ollama import Ollama
        model = Ollama(model=model_name)
 
    response_text = model.invoke(prompt)
    sources = [chunk.id for chunk in chunks]
 
    return RagResponse(
        query_text=query_text,
        response_text=response_text,
        sources=sources,
        context_text=context_text,
        prompt=prompt,
        chunks=chunks,
    )
 
 
def query_rag(query_text: str, **kwargs: Any) -> str:
    return query_rag_response(query_text, **kwargs).response_text
 
 
def format_response(response: RagResponse) -> str:
    return f"Response: {response.response_text}\nSources: {response.sources}"
 
 
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--k", type=int, default=DEFAULT_RESULT_COUNT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
 
    response = query_rag_response(args.query_text, model_name=args.model, k=args.k)
 
    if args.json:
        print(json.dumps(response.to_dict(), indent=2))
        return
 
    print(format_response(response))
 
 
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        main()
    else:
        print("AI Server starting on port 8000...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
 