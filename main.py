import os
import requests
import telebot
from telebot.types import ForceReply
from threading import Thread
import time
import re
import json
from queue import Queue # কিউ সিস্টেমের জন্য

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
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

def load_db():
    global db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            try:
                db = json.load(f)
            except json.JSONDecodeError:
                db = {'users': {}}
    else:
        db = {'users': {}}

# --- Queue System ---
upload_queue = Queue()

# --- Helper Functions ---
def is_url(text):
    url_pattern = re.compile(
        r'^(?:http|ftp)s?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(url_pattern, text) is not None

def is_admin(user_id):
    return user_id == ADMIN_ID

def get_user(user_id):
    user_id_str = str(user_id)
    if 'users' not in db:
        db['users'] = {}
    if user_id_str not in db['users']:
        db['users'][user_id_str] = {'api_key': None, 'custom_domain': None}
    return db['users'][user_id_str]

# --- Background Upload Processing ---
def process_upload_from_url(message, url):
    user_id = message.chat.id
    user_data = get_user(user_id)
    api_key = user_data.get('api_key')
    
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
        message, url = upload_queue.get()
        if message is None: # A way to stop the thread if needed
            break
        try:
            process_upload_from_url(message, url)
        except Exception as e:
            print(f"Error in worker processing task: {e}")
        finally:
            upload_queue.task_done()

# --- User Handlers ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    get_user(user_id)
    save_db()
    
    welcome_text = (f"👋 Hello, {message.from_user.first_name}!\n\n"
                    "Welcome to the advanced RPM Share Uploader Bot.\n"
                    "To get started, you need to set your RPM Share API Key.\n\n"
                    "➡️ Use the command: `/setkey YOUR_API_KEY`\n\n"
                    "💡 Use /help to see all commands.\n\n"
                    "__Created by: MD SALMAN__")
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['setkey'])
def set_api_key(message):
    try:
        key = message.text.split(maxsplit=1)[1].strip()
        user_data = get_user(message.from_user.id)
        user_data['api_key'] = key
        save_db()
        bot.reply_to(message, "✅ Your RPM Share API Key has been saved successfully!")
    except IndexError:
        bot.reply_to(message, "⚠️ Please provide an API Key.\n*Usage:* `/setkey YOUR_API_KEY`")

@bot.message_handler(commands=['setdomain'])
def set_custom_domain(message):
    try:
        domain = message.text.split(maxsplit=1)[1].strip()
        if not is_url(domain):
            bot.reply_to(message, "❌ Invalid URL format.")
            return
        
        user_data = get_user(message.from_user.id)
        user_data['custom_domain'] = domain
        save_db()
        bot.reply_to(message, f"✅ Your custom domain has been set to:\n`{domain}`")
    except IndexError:
        bot.reply_to(message, "⚠️ Please provide a domain URL.\n*Usage:* `/setdomain https://your-site.com/`")

@bot.message_handler(commands=['my_settings'])
def show_my_settings(message):
    user_data = get_user(message.from_user.id)
    api_key = user_data.get('api_key')
    domain = user_data.get('custom_domain') or f"{DEFAULT_DOMAIN} (Default)"
    
    settings_text = ("⚙️ **Your Current Settings**\n\n"
                     f"🔑 **API Key:** `{'********' + api_key[-4:] if api_key else 'Not Set'}`\n"
                     f"🌐 **Domain URL:** `{domain}`")
    bot.reply_to(message, settings_text)

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = ("**Here's how to use me:**\n"
                 "1️⃣ Set your RPM Share API Key:\n`/setkey YOUR_API_KEY`\n\n"
                 "2️⃣ (Optional) Set your custom domain URL:\n`/setdomain https://your-site.com/`\n\n"
                 "3️⃣ Send me any direct download link to upload.\n\n"
                 "**Other Commands:**\n"
                 "`/my_settings` - View your saved settings.")
    if is_admin(message.from_user.id):
        help_text += ("\n\n👑 **Admin Commands:**\n"
                      "/stats - Get user statistics.\n"
                      "/broadcast <message> - Send a message to all users.")
    bot.reply_to(message, help_text)

@bot.message_handler(func=lambda message: is_url(message.text))
def handle_url(message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    
    if not user_data.get('api_key'):
        bot.reply_to(message, "❌ **API Key not set!**\nPlease use `/setkey` first.")
        return

    url = message.text
    upload_queue.put((message, url))
    queue_position = upload_queue.qsize()
    bot.reply_to(message, f"✅ Your link has been added to the queue.\n**Position:** `{queue_position}`")

# --- Admin Handlers ---
@bot.message_handler(commands=['stats'])
def get_stats(message):
    if not is_admin(message.from_user.id):
        return
    total_users = len(db.get('users', {}))
    bot.reply_to(message, f"📊 **Total Users:** {total_users}\n📝 **Tasks in Queue:** {upload_queue.qsize()}")

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if not is_admin(message.from_user.id):
        return
    try:
        broadcast_text = message.text.split(maxsplit=1)[1]
    except IndexError:
        bot.reply_to(message, "Usage: `/broadcast <message>`")
        return
    
    users = db.get('users', {}).keys()
    status_msg = bot.reply_to(message, f"📣 Broadcasting to {len(users)} users...")
    sent, failed = 0, 0
    for user_id_str in users:
        try:
            bot.send_message(int(user_id_str), broadcast_text)
            sent += 1
        except Exception:
            failed += 1
        time.sleep(0.1)
    result_text = f"✅ Broadcast Complete!\n\nSent: {sent}\nFailed: {failed}"
    bot.edit_message_text(result_text, status_msg.chat.id, status_msg.message_id)
    save_db()

# --- Main Execution ---
if __name__ == "__main__":
    load_db()
    
    worker_thread = Thread(target=worker, daemon=True)
    worker_thread.start()
    
    print("Bot is starting... Worker thread is running.")
    print(f"Admin ID is set to: {ADMIN_ID}")
    bot.infinity_polling(none_stop=True)
