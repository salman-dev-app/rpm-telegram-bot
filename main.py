import os
import requests
import telebot
from telebot.types import ForceReply
from threading import Thread
import time
import re
import json
from queue import Queue # নতুন কিউ সিস্টেমের জন্য

# --- Bot Configuration ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')
DEFAULT_DOMAIN = os.environ.get('DEFAULT_DOMAIN', 'https://aniwavelite.rpmlive.online/')

if not all([BOT_TOKEN, ADMIN_ID]):
    print("FATAL ERROR: BOT_TOKEN or ADMIN_ID environment variables are missing!")
    exit()

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    print("FATAL ERROR: ADMIN_ID must be a valid integer!")
    exit()

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# --- Persistent JSON Database ---
DB_FILE = "bot_database.json"
db = {}

def save_db():
    # ... (no change)
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

def load_db():
    # ... (no change)
    global db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            db = json.load(f)
    else:
        db = {'users': {}}

# --- START: নতুন কিউ সিস্টেম ---
upload_queue = Queue()

# --- Helper Functions (অপরিবর্তিত) ---
def is_url(text): #...
def is_admin(user_id): #...
def get_user(user_id): #...

# --- Background Upload Processing ---
# এই ফাংশনটি এখন সরাসরি কল না হয়ে, কিউ থেকে কল হবে
def process_upload_from_url(message, url):
    # ... (এই ফাংশনের ভেতরের সবকিছু অপরিবর্তিত)
    user_id = message.chat.id
    user_data = get_user(user_id)
    api_key = user_data.get('api_key')
    
    if not api_key:
        bot.send_message(user_id, "❌ **API Key not set!**\nPlease use `/setkey` to set your API Key first.")
        return

    status_msg = bot.send_message(user_id, f"▶️ **Starting upload for:**\n`{url}`")
    file_path_on_disk = None
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        bot.edit_message_text("📥 **Downloading...**", status_msg.chat.id, status_msg.message_id)
        filename = url.split('/')[-1].split('?')[0] or f"downloaded_file_{int(time.time())}"
        file_path_on_disk = filename
        
        with requests.get(url, stream=True, timeout=3600, headers=headers) as r:
            r.raise_for_status()
            with open(file_path_on_disk, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024): f.write(chunk)

        bot.edit_message_text("✅ **Download Complete!**\n\n⬆️ **Uploading to RPM Share...**", status_msg.chat.id, status_msg.message_id)

        server_url_endpoint = f"https://rpmshare.com/api/upload/server?key={api_key}"
        server_response = requests.get(server_url_endpoint, headers=headers)
        server_data = server_response.json()
        if server_data.get("status") != 200: raise Exception(server_data.get('msg', 'Could not get RPM server.'))
        
        actual_upload_url = server_data["result"]
        
        with open(file_path_on_disk, 'rb') as f:
            files_to_upload = {'file': (file_path_on_disk, f)}
            payload = {'key': api_key}
            upload_response = requests.post(actual_upload_url, files=files_to_upload, data=payload, headers=headers, timeout=3600)
            upload_data = upload_response.json()

        if upload_data.get("status") == 200 and upload_data.get("files"):
            file_code = upload_data["files"][0]["filecode"]
            base_url = user_data.get('custom_domain') or DEFAULT_DOMAIN
            if not base_url.endswith('/'): base_url += '/'
            download_link = f"{base_url}#{file_code}"
            final_message = (f"✅ **Upload Successful!**\n\n🔗 **Your Embed Link:**\n`{download_link}`")
            bot.edit_message_text(final_message, status_msg.chat.id, status_msg.message_id)
        else:
            raise Exception(upload_data.get('msg', 'Upload failed.'))

    except Exception as e:
        error_text = f"❌ **An error occurred with:** `{url}`\n\n`{e}`"
        bot.edit_message_text(error_text, status_msg.chat.id, status_msg.message_id)
    finally:
        if file_path_on_disk and os.path.exists(file_path_on_disk):
            os.remove(file_path_on_disk)
        save_db()


# --- Worker Function (কিউ থেকে কাজ নেওয়ার জন্য) ---
def worker():
    while True:
        # কিউ থেকে একটি আইটেম (কাজ) নাও
        message, url = upload_queue.get()
        
        # কাজটি প্রসেস করো
        process_upload_from_url(message, url)
        
        # কাজ শেষ হয়েছে বলে চিহ্নিত করো
        upload_queue.task_done()

# --- User Handlers (ব্যবহারকারীর কমান্ড হ্যান্ডেল করার জন্য) ---

@bot.message_handler(func=lambda message: is_url(message.text))
def handle_url(message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    
    # API Key সেট করা আছে কিনা তা পরীক্ষা করা
    if not user_data.get('api_key'):
        bot.reply_to(message, "❌ **API Key not set!**\nPlease use `/setkey <your_api_key>` to set your API Key first.")
        return

    # কাজটি কিউতে যোগ করা
    url = message.text
    upload_queue.put((message, url))
    
    # ব্যবহারকারীকে তার সিরিয়াল নম্বর জানানো
    queue_position = upload_queue.qsize()
    bot.reply_to(message, f"✅ Your link has been added to the queue.\n**Position:** `{queue_position}`")

# ... (আপনার বাকি সব কমান্ড /start, /setkey, /setdomain, /help, /stats, /broadcast অপরিবর্তিত থাকবে)
@bot.message_handler(commands=['start']) #...
@bot.message_handler(commands=['setkey']) #...
@bot.message_handler(commands=['setdomain']) #...
@bot.message_handler(commands=['my_settings']) #...
@bot.message_handler(commands=['help']) #...
@bot.message_handler(commands=['stats']) #...
@bot.message_handler(commands=['broadcast']) #...
# (For brevity, I'm not pasting them again. Just keep them as they were in the previous code)

# --- Main Execution ---
if __name__ == "__main__":
    load_db()
    
    # --- Worker থ্রেডটি চালু করা ---
    worker_thread = Thread(target=worker, daemon=True)
    worker_thread.start()
    
    print("Bot is starting... Worker thread is running.")
    print(f"Admin ID is set to: {ADMIN_ID}")
    bot.infinity_polling(none_stop=True)
