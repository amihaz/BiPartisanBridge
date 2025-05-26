# models.py

from dotenv import load_dotenv
from langchain import LLMChain, PromptTemplate
from langchain.chat_models import ChatOpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_API_BASE
load_dotenv()

# ─── OpenRouter LLM Setup ──────────────────────────────────────────────────────

llm = ChatOpenAI(
    model_name="deepseek/deepseek-chat:free",
    temperature=0,
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base=OPENROUTER_API_BASE
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
