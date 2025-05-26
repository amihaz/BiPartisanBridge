import asyncio
import json
from datetime import datetime, timedelta
from collections import defaultdict
from telethon import TelegramClient, events
from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    LEFT_CHANNELS,
    RIGHT_CHANNELS,
    TARGET_CHANNEL,
    TOPIC_THRESHOLD,
    MESSAGE_TTL_HOURS,
)
from models import summarization_chain, unified_chain, cluster_chain
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
import json
import uuid

# Initialize Telethon client with user session
client = TelegramClient("session", TELEGRAM_API_ID, TELEGRAM_API_HASH)

# In-memory buffer: channel_id -> list of messages with ts and chan
channel_buffers = defaultdict(list)

@client.on(events.NewMessage(chats=LEFT_CHANNELS + RIGHT_CHANNELS))
async def collect(event):
    print(event)
    chat_id = str(event.chat_id)
    msg = event.message.message
    if msg:
        channel_buffers[chat_id].append({
            "msg": msg,
            "ts": datetime.utcnow(),
            "chan": chat_id
        })

async def cluster_messages(entries, topic_threshold):
    """
    Clusters messages using LLM and filters by unique channel threshold.

    Args:
        entries (list): A list of tuples (channel_id, message_text)
        topic_threshold (int): Minimum number of unique channels per topic to include

    Returns:
        valid_clusters (dict): {topic_title: [ {"id": ..., "channel": ...}, ... ]}
        id_map (dict): {uuid: {"channel": ..., "message": ...}}
    """

    # Assign unique IDs to each message
    id_map = {}
    lines = []
    for chan, msg in entries:
        mid = str(uuid.uuid4())
        id_map[mid] = {"channel": chan, "message": msg}
        lines.append(f"[{mid}][{chan}] {msg}")

    # Build batch for the LLM
    batch = "\n".join(lines)

    # Call the LLM via the cluster_chain
    try:
        clusters_str = await cluster_chain.arun(messages=batch)
        clusters = json.loads(clusters_str)
    except Exception as e:
        print(f"[cluster_messages] Failed to parse LLM response: {e}")
        return {}, id_map

    # Filter by unique channel threshold
    valid_clusters = {}
    for title, items in clusters.items():
        unique_chans = {item["channel"] for item in items}
        if len(unique_chans) >= topic_threshold:
            valid_clusters[title] = items

    return valid_clusters, id_map

async def summarize_loop():
    await asyncio.sleep(10)
    ttl = timedelta(hours=MESSAGE_TTL_HOURS)
    while True:
        await asyncio.sleep(600)
        print("channel_buffers: ", channel_buffers)
        now = datetime.utcnow()
        for chan in list(channel_buffers):
            channel_buffers[chan] = [e for e in channel_buffers[chan] if now - e["ts"] < ttl]
        print("channel_buffers after ttl: ", channel_buffers)
        entries = [(e["chan"], e["msg"]) for sub in channel_buffers.values() for e in sub]
        print("entries: ", entries)
        if not entries:
            continue

        valid_clusters, id_map = await cluster_messages(entries, TOPIC_THRESHOLD)
        print("valid_clusters: ", valid_clusters)
        print("id_map: ", id_map)
        if not valid_clusters:
            continue

        parts = [
            f"**Topic Digest ({len(valid_clusters)} topics)**",
            f"Digest of topics mentioned by at least {TOPIC_THRESHOLD} channels."
        ]
        processed_ids = set()

        for topic, items in valid_clusters.items():
            left_msgs = [id_map[it["id"]]["message"] for it in items if it["channel"] in LEFT_CHANNELS]
            right_msgs = [id_map[it["id"]]["message"] for it in items if it["channel"] in RIGHT_CHANNELS]

            left_summary = await summarization_chain.arun(topic=topic, text="\n".join(left_msgs)) if left_msgs else ""
            right_summary = await summarization_chain.arun(topic=topic, text="\n".join(right_msgs)) if right_msgs else ""

            unified = await unified_chain.arun(
                topic=topic,
                left_summary=left_summary,
                right_summary=right_summary
            )
            title_line, desc_line = unified.split("\n", 1)

            parts.extend([
                f"## {title_line}\n{desc_line}",
                f"**Left Perspective:**\n{left_summary}",
                f"**Right Perspective:**\n{right_summary}"
            ])
            processed_ids.update(it["id"] for it in items)

        final = "\n\n".join(parts)
        await client.send_message(TARGET_CHANNEL, final)

        for chan in channel_buffers:
            channel_buffers[chan] = [e for e in channel_buffers[chan] if e["msg"] not in [id_map[mid]["message"] for mid in processed_ids]]

async def main():
    await client.start()
    asyncio.create_task(summarize_loop())
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
