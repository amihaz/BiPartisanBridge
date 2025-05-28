# models.py

import openai
import json
from config import OPENROUTER_API_KEY, OPENROUTER_API_BASE

# Initialize OpenAI client for OpenRouter
openai_client = openai.AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_API_BASE,
)

async def call_llm(prompt_text):
    """
    Direct OpenAI API call to OpenRouter to avoid LangChain compatibility issues
    
    Args:
        prompt_text (str): The prompt to send to the LLM
        
    Returns:
        str: The LLM response content, or None if there was an error
    """
    try:
        response = await openai_client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0
        )
        print("response: ", response)
        return response.choices[0].message.content
    except Exception as e:
        print(f"[call_llm] Error: {e}")
        return None

async def cluster_messages_llm(entries, topic_threshold):
    """
    Clusters messages using LLM and filters by unique channel threshold.

    Args:
        entries (list): A list of tuples (channel_id, message_text)
        topic_threshold (int): Minimum number of unique channels per topic to include

    Returns:
        tuple: (valid_clusters dict, id_map dict)
            - valid_clusters: {topic_title: [{"id": ..., "channel": ...}, ...]}
            - id_map: {uuid: {"channel": ..., "message": ...}}
    """
    import uuid
    
    id_map = {}
    lines = []
    
    # Create unique IDs for each message
    for chan, msg in entries:
        mid = str(uuid.uuid4())
        id_map[mid] = {"channel": chan, "message": msg}
        lines.append(f"ID: {mid} | Channel: {chan} | Message: {msg}")

    batch = "\n".join(lines)
    print("[DEBUG] batch:\n", batch)

    # Create the clustering prompt
    cluster_prompt = f"""
You are given a list of messages, each tagged with a unique ID and a channel.
Your job: group them into topic clusters and output **only** a raw JSON object—nothing else.

Requirements:
1. Raw JSON only—no markdown, no code fences, no extra text.
2. JSON object keys (cluster titles) may use only letters, numbers, spaces, and hyphens.
   - Do not include any double-quote character (") in the titles.
   - If needed, replace internal quotes with apostrophes (’).
3. Escape all double quotes in message fields (id or channel) with a backslash.
4. Follow exactly this format:

{{
  "<Cluster Title>": [
    {{ "id": "<uuid>", "channel": "<channel_id>" }},
    …  
  ],
  …  
}}

Here are the messages to cluster:
{batch}

Answer in the same language as the messages.
"""

    try:
        response = await call_llm(cluster_prompt)
        if not response:
            print("[cluster_messages] No response from LLM")
            return {}, id_map
            
        print(f"[DEBUG] LLM raw output:\n", response)
        
        # Clean up the response string if needed
        response_str = response.strip()
        if response_str.startswith('```json'):
            response_str = response_str[7:-3].strip()
        elif response_str.startswith('```'):
            response_str = response_str[3:-3].strip()
        
        print(f"[DEBUG] response_str:\n", response_str)

        clusters = json.loads(response_str)
        print(f"[DEBUG] clusters:\n", clusters)

    except Exception as e:
        print(f"[cluster_messages] Failed to parse LLM response: {e}")
        print(f"[cluster_messages] Raw response: {response}")
        import traceback
        traceback.print_exc()
        return {}, id_map

    # Filter clusters by unique channel threshold
    valid_clusters = {}
    for title, items in clusters.items():
        unique_chans = {item["channel"] for item in items}
        print("title: ", title)
        print("unique_chans: ", unique_chans)
        print("len(unique_chans): ", len(unique_chans))
        print("topic_threshold: ", topic_threshold)
        if len(unique_chans) >= topic_threshold:
            valid_clusters[title] = items
            print(f"[DEBUG] valid_clusters:\n", valid_clusters)

    return valid_clusters, id_map

async def summarize_messages_llm(topic, messages_text):
    """
    Summarize messages for a given topic. Answer always in the same language as the messages.
    
    Args:
        topic (str): The topic title
        messages_text (str): The messages to summarize
        
    Returns:
        str: The summary, or empty string if error
    """
    if not messages_text.strip():
        return ""
        
    summarize_prompt = f"""
Summarize the following messages under topic '{topic}'. Answer always in the same language as the messages.
{messages_text}
"""
    
    result = await call_llm(summarize_prompt)
    return result if result else ""

async def create_unified_title_description_llm(topic, left_summary, right_summary):
    """
    Create a balanced title and description from left and right summaries. Answer always in the same language as the summaries.
    
    Args:
        topic (str): The topic title
        left_summary (str): Summary from left-leaning sources
        right_summary (str): Summary from right-leaning sources
        
    Returns:
        dict: {"title": "...", "description": "..."} or fallback values
    """
    unified_prompt = f"""
Topic: {topic}

Left summary:
{left_summary}

Right summary:
{right_summary}

Create a balanced title and a neutral description for this topic. Answer always in the same language as the summaries.
Return a JSON object in the following format: {{ "title": "...", "description": "..." }}
Return *only* a valid JSON object (no markdown fences).  
Escape all internal double‐quotes as `\"`.  
"""
    
    unified_content = await call_llm(unified_prompt)

    print(f"[DEBUG] unified_content:\n", unified_content)

    response_str = unified_content.strip()
    if response_str.startswith('```json'):
        response_str = response_str[7:-3].strip()
    elif response_str.startswith('```'):
        response_str = response_str[3:-3].strip()
    
    print(f"[DEBUG] response_str:\n", response_str)

    if not response_str:
        return {"title": topic, "description": "No description available"}
    
    try:
        # Try to parse as JSON first
        unified_json = json.loads(response_str.strip())
        return {
            "title": unified_json.get("title", topic),
            "description": unified_json.get("description", "")
        }
    except json.JSONDecodeError:
        # Fallback to splitting by newline
        lines = unified_content.split("\n", 1)
        return {
            "title": lines[0] if lines else topic,
            "description": lines[1] if len(lines) > 1 else ""
        }