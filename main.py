# main.py

import asyncio
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import traceback
from telethon import TelegramClient, events

from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    LEFT_CHANNELS,
    RIGHT_CHANNELS,
    TARGET_CHANNEL_ID,
    TOPIC_THRESHOLD,
    MESSAGE_TTL_HOURS,
)

from models import (
    cluster_messages_llm,
    summarize_messages_llm,    
    create_unified_title_description_llm
)
from telegram import init_channel_ids, is_left_channel, is_right_channel

# Initialize Telethon client with user session
client = TelegramClient("session", TELEGRAM_API_ID, TELEGRAM_API_HASH)

# In-memory buffer: channel_id -> list of messages with timestamp and channel info
channel_buffers = defaultdict(list)

@client.on(events.NewMessage(chats=LEFT_CHANNELS + RIGHT_CHANNELS))
async def collect(event):
    """Collect incoming messages from monitored channels"""
    print(f"[COLLECT] New message from chat {event.chat_id}: {event.message.message}")
    chat_id = str(event.chat_id)
    msg = event.message.message
    
    if msg:
        channel_buffers[chat_id].append({
            "msg": msg,
            "ts": datetime.now(timezone.utc),
            "chan": chat_id
        })
        print(f"[COLLECT] Added message to buffer. Buffer size for {chat_id}: {len(channel_buffers[chat_id])}")

async def summarize_loop():
    """Main processing loop that runs every 10 seconds"""
    await asyncio.sleep(10)  # Initial delay
    ttl = timedelta(hours=MESSAGE_TTL_HOURS)
    
    while True:
        try:
            await asyncio.sleep(10)  # Process every 10 seconds (change to 600 for 10 minutes)
            print(f"[LOOP] Starting processing cycle at {datetime.now(timezone.utc)}")
            print(f"[LOOP] Current channel_buffers: {dict(channel_buffers)}")
            
            # Remove expired messages based on TTL
            now = datetime.now(timezone.utc)
            for chan in list(channel_buffers):
                original_count = len(channel_buffers[chan])
                channel_buffers[chan] = [e for e in channel_buffers[chan] if now - e["ts"] < ttl]
                new_count = len(channel_buffers[chan])
                if original_count != new_count:
                    print(f"[LOOP] Removed {original_count - new_count} expired messages from {chan}")
            
            print(f"[LOOP] channel_buffers after TTL cleanup: {dict(channel_buffers)}")
            
            # Flatten all messages into entries list
            entries = [(e["chan"], e["msg"]) for sub in channel_buffers.values() for e in sub]
            print(f"[LOOP] Total entries to process: {len(entries)}")
            
            if not entries:
                print("[LOOP] No entries to process, continuing...")
                continue

            # Cluster messages using LLM
            print("[LOOP] Clustering messages...")
            valid_clusters, id_map = await cluster_messages_llm(entries, TOPIC_THRESHOLD)
            print(f"[LOOP] Found {len(valid_clusters)} valid clusters")
            print(f"[LOOP] valid_clusters: {valid_clusters}")
            print(f"[LOOP] id_map: {id_map}")
            
            if not valid_clusters:
                print("[LOOP] No valid clusters found, continuing...")
                continue

            # Build the digest message
            parts = []
            processed_ids = set()

            for topic, items in valid_clusters.items():
                print(f"[LOOP] Processing topic: {topic}")
                
                # Separate messages by left/right channels
                left_msgs  = [id_map[it["id"]]["message"] for it in items if is_left_channel(it["channel"])]                
                right_msgs = [id_map[it["id"]]["message"] for it in items if is_right_channel(it["channel"])]
                
                print(f"[LOOP] Topic '{topic}': {len(left_msgs)} left msgs, {len(right_msgs)} right msgs")

                # Generate summaries for each perspective
                left_summary = ""
                right_summary = ""
                
                if left_msgs:
                    print(f"[LOOP] Summarizing left messages for topic: {topic}")
                    left_summary = await summarize_messages_llm(topic, "\n".join(left_msgs))
                
                if right_msgs:
                    print(f"[LOOP] Summarizing right messages for topic: {topic}")
                    right_summary = await summarize_messages_llm(topic, "\n".join(right_msgs))

                # Create unified title and description
                print(f"[LOOP] Creating unified title/description for topic: {topic}")
                unified_result = await create_unified_title_description_llm(topic, left_summary, right_summary)
                print(f"[LOOP] Unified result: {unified_result}")
                title_line = unified_result["title"]
                desc_line = unified_result["description"]

                # Add to digest parts
                parts.extend([
                    f"**{title_line}**\n\n{desc_line}",
                    f"**Left Perspective:**\n{left_summary}",
                    f"**Right Perspective:**\n{right_summary}"
                ])
                
                print(f"[LOOP] Parts: {parts}")

                # Track processed message IDs
                processed_ids.update(it["id"] for it in items)

            # Send the digest to target channel
            final_message = "\n\n".join(parts)
            print(f"[LOOP] Sending digest message to target channel {TARGET_CHANNEL_ID}")
            print(f"[LOOP] Final message: {final_message}")
            
            await client.send_message(TARGET_CHANNEL_ID, final_message)
            print("[LOOP] Digest sent successfully!")

            # Remove processed messages from buffers
            processed_messages = {id_map[mid]["message"] for mid in processed_ids}
            for chan in channel_buffers:
                original_count = len(channel_buffers[chan])
                channel_buffers[chan] = [e for e in channel_buffers[chan] 
                                       if e["msg"] not in processed_messages]
                new_count = len(channel_buffers[chan])
                if original_count != new_count:
                    print(f"[LOOP] Removed {original_count - new_count} processed messages from {chan}")

        except Exception as e:
            print(f"[LOOP] Error in summarize_loop: {e}")
            traceback.print_exc()
            # Continue the loop even if there's an error

async def main():
    """Main entry point"""
    print("[MAIN] Starting Telegram client...")
    await client.start()
    print("[MAIN] Client started successfully!")
    
    print(f"[MAIN] Monitoring channels: LEFT={LEFT_CHANNELS}, RIGHT={RIGHT_CHANNELS}")
    print(f"[MAIN] Target channel: {TARGET_CHANNEL_ID}")
    print(f"[MAIN] Topic threshold: {TOPIC_THRESHOLD}")
    print(f"[MAIN] Message TTL: {MESSAGE_TTL_HOURS} hours")
    
    await init_channel_ids(client)

    # Start the processing loop
    print("[MAIN] Starting summarize loop...")
    asyncio.create_task(summarize_loop())
    
    print("[MAIN] Bot is running! Press Ctrl+C to stop.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[MAIN] Bot stopped by user")
    except Exception as e:
        print(f"[MAIN] Fatal error: {e}")
        traceback.print_exc()