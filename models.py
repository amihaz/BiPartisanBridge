# models.py

import os
import json
import uuid
from dotenv import load_dotenv
from langchain import LLMChain, PromptTemplate
from langchain.chat_models import ChatOpenAI

load_dotenv()

# ─── OpenRouter LLM Setup ──────────────────────────────────────────────────────
api_key  = os.getenv("OPENROUTER_API_KEY")
api_base = os.getenv(
    "OPENROUTER_API_BASE",
    "https://openrouter.ai/v1/chat/completions"
)
if not api_key:
    raise ValueError("You must set OPENROUTER_API_KEY")

llm = ChatOpenAI(
    model_name="deepseek/deepseek-chat:free",
    temperature=0,
    openai_api_key=api_key,
    openai_api_base=api_base
)

# ─── Prompt & Chain: Clustering ───────────────────────────────────────────────
cluster_prompt = PromptTemplate(
    template="""
Group these annotated messages into clusters describing the same event or topic.
Return JSON: keys = cluster titles (3–5 words), 
values = lists of objects {{ "id": "<UUID>", "channel": "<channel_id>" }}.

Messages:
{messages}
""",
    input_variables=["messages"]
)
cluster_chain = LLMChain(llm=llm, prompt=cluster_prompt)

# ─── Prompt & Chain: Summarization ────────────────────────────────────────────
summarize_prompt = PromptTemplate(
    template="""
Summarize the following messages under topic '{topic}':
{text}
""",
    input_variables=["topic", "text"]
)
summarization_chain = LLMChain(llm=llm, prompt=summarize_prompt)

# ─── Prompt & Chain: Unified Title/Description ───────────────────────────────
unified_prompt = PromptTemplate(
    template="""
Topic: {topic}

Left summary:
{left_summary}

Right summary:
{right_summary}

Create a balanced title and a neutral description for this topic.
Return JSON: {{ "title": "...", "description": "..." }}
""",
    input_variables=["topic", "left_summary", "right_summary"]
)
unified_chain = LLMChain(llm=llm, prompt=unified_prompt)

async def cluster_messages(message_topics, topic_threshold):
    """
    message_topics: list of (channel_id, message_text)
    Returns (valid_clusters, id_map):
      - valid_clusters: { topic_title: [ {id,channel}, ... ] } filtered by threshold
      - id_map: { id: {"channel":..., "message":...} }
    """
    # 1) Annotate each message with a random UUID
    id_map = {}
    lines  = []
    for chan, msg in message_topics:
        mid = str(uuid.uuid4())
        id_map[mid] = {"channel": chan, "message": msg}
        lines.append(f"[{mid}][{chan}] {msg}")

    # 2
