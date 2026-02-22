import telebot
from telebot import types
import json
import os
import re
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------- CONFIGURATION ----------------
TOKEN = "8023775596:AAFJsXQEv6XUjyzRR9OGbhy0JU_Q2yTP77Q"
ADMIN_ID = 6668016879

# ---------------- ROBUST SESSION (Anti-Crash) ----------------
def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# Create bot instance with custom session
bot = telebot.TeleBot(TOKEN)
bot.session = create_session()
bot.request_timeout = 120

USERS_FILE = "users.json"
BANNED_FILE = "banned.json"
DOWNLOAD_FILE = "downloads.json"
SETTINGS_FILE = "settings.json"

# ---------------- FILE SYSTEM ----------------
def load_data(file, default=None):
    if default is None:
        default = []
    if not os.path.exists(file):
        return default
    try:
        with open(file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default

def save_data(file, data):
    try:
        with open(file, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving file {file}: {e}")

users = set(load_data(USERS_FILE, []))
banned = set(load_data(BANNED_FILE, []))
downloads = load_data(DOWNLOAD_FILE, {"lite": 0, "seven": 0})
settings = load_data(SETTINGS_FILE, {"maintenance": False})

def save_users():
    save_data(USERS_FILE, list(users))

def save_banned():
    save_data(BANNED_FILE, list(banned))

def save_downloads():
    save_data(DOWNLOAD_FILE, downloads)

def save_settings():
    save_data(SETTINGS_FILE, settings)

def add_user(user_id):
    if user_id not in users:
        users.add(user_id)
        save_users()

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if user_id in banned:
        try:
            bot.send_message(user_id, "🚫 You are banned from using this bot.")
        except Exception:
            pass
        return

    if settings.get("maintenance", False) and user_id != ADMIN_ID:
        try:
            bot.send_message(user_id, "⚠️ Bot is currently under maintenance. Please try again later.")
        except Exception:
            pass
        return

    add_user(user_id)
    show_main_menu(user_id)

def show_main_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📩 Send Message", callback_data="send"))
   

    if chat_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("👑 Admin Panel", callback_data="admin"))

    try:
        bot.send_message(chat_id, "👋 Welcome to Fast Account Professional Bot", reply_markup=markup)
    except Exception as e:
        print(f"Failed to send menu to {chat_id}: {e}")

# ---------------- CALLBACK ----------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.message.chat.id

    if user_id in banned:
        return

    if settings.get("maintenance", False) and user_id != ADMIN_ID:
        try:
            bot.answer_callback_query(call.id, "⚠️ Bot under maintenance.", show_alert=True)
        except:
            pass
        return

    try:
        if call.data == "send":
            msg = bot.send_message(user_id, "✍️ Write your message:")
            bot.register_next_step_handler(msg, forward_to_admin)

        elif call.data == "help":
            bot.send_message(user_id, "Use buttons to navigate.\n\nDownload accounts using the buttons below.")
elif call.data == "lite":
    send_apk(user_id, "lite.apk", "lite")

elif call.data == "seven":
    send_apk(user_id, "seven.apk", "seven")
        elif call.data == "lite":
            send_apk(user_id, "lite.apk", "lite")

        elif call.data == "seven":
            send_apk(user_id, "seven.apk", "seven")

        elif call.data == "admin" and user_id == ADMIN_ID:
            admin_panel(user_id)

        elif call.data.startswith("admin_") and user_id == ADMIN_ID:
            handle_admin_callbacks(call)
            
        elif call.data == "back_start":
            try:
                bot.delete_message(user_id, call.message.message_id)
            except:
                pass
            show_main_menu(user_id)
            
    except Exception as e:
        print(f"Callback error: {e}")
        try:
            bot.answer_callback_query(call.id, "An error occurred.")
        except:
            pass

# ---------------- APK SEND ----------------
def send_apk(chat_id, file_name, key):
    if not os.path.exists(file_name):
        try:
            bot.send_message(chat_id, "❌ File not found. Contact admin.")
        except:
            pass
        return

    # Update count silently
    global downloads
    downloads = load_data(DOWNLOAD_FILE, {"lite": 0, "seven": 0})
    downloads[key] += 1
    save_downloads()

    # Robust sending loop
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            with open(file_name, "rb") as f:
                bot.send_document(chat_id, f, caption="⬇ Download Started", timeout=120)
            break
        except Exception as e:
            retry_count += 1
            print(f"Error sending APK (Attempt {retry_count}/{max_retries}): {e}")
            if retry_count == max_retries:
                try:
                    bot.send_message(chat_id, "❌ Failed to send file due to network issues. Please try again later.")
                except:
                    pass
            else:
                time.sleep(3)

# ---------------- FORWARD SYSTEM ----------------
def forward_to_admin(message):
    user_id = message.chat.id
    if user_id in banned:
        return

    user = message.from_user
    details = (
        f"📩 <b>New Message</b>\n"
        f"<b>User ID:</b> <code>{user_id}</code>\n"
        f"<b>Name:</b> {user.first_name} {user.last_name or ''}\n"
        f"<b>Username:</b> @{user.username if user.username else 'None'}\n"
        f"#ID_{user_id}" 
    )

    try:
        if message.content_type == 'text':
            bot.send_message(ADMIN_ID, f"{details}\n\n<b>Message:</b>\n{message.text}", parse_mode='HTML')
        else:
            caption = message.caption if message.caption else ""
            if len(caption) + len(details) > 1024:
                bot.copy_message(ADMIN_ID, user_id, message.message_id)
                bot.send_message(ADMIN_ID, details, parse_mode='HTML')
            else:
                bot.copy_message(ADMIN_ID, user_id, message.message_id, caption=f"{caption}\n\n{details}", parse_mode='HTML')
        
        bot.send_message(user_id, "✅ Message sent to admin!")
    except Exception as e:
        print(f"Forward error: {e}")
        try:
            bot.send_message(user_id, "❌ Failed to send message. Network Error.")
        except:
            pass

# ---------------- ADMIN REPLY ----------------
@bot.message_handler(func=lambda m: m.reply_to_message is not None)
def admin_reply(message):
    if message.chat.id != ADMIN_ID:
        return

    target_user = None
    source_text = message.reply_to_message.text or message.reply_to_message.caption or ""
    match = re.search(r'#ID_(\d+)', source_text)
    
    if match:
        target_user = int(match.group(1))

    if target_user:
        try:
            bot.copy_message(target_user, ADMIN_ID, message.message_id)
            bot.send_message(ADMIN_ID, f"✅ Reply sent to user {target_user}")
        except Exception as e:
            bot.send_message(ADMIN_ID, f"❌ Failed to send reply.\nError: {e}")
    else:
        bot.send_message(ADMIN_ID, "❌ Could not identify user.")

# ---------------- ADMIN PANEL ----------------
def admin_panel(chat_id):
    status = "ON 🔴" if settings.get("maintenance") else "OFF 🟢"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"))
    markup.add(types.InlineKeyboardButton("👥 User Count", callback_data="admin_count"))
    markup.add(types.InlineKeyboardButton("📊 Download Stats", callback_data="admin_stats"))
    markup.add(types.InlineKeyboardButton(f"⚙️ Maintenance: {status}", callback_data="admin_maintenance"))
    markup.add(types.InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_prompt"))
    markup.add(types.InlineKeyboardButton("✅ Unban User", callback_data="admin_unban_prompt"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="back_start"))
    
    try:
        bot.send_message(chat_id, "👑 <b>Admin Panel</b>", reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        print(f"Admin panel error: {e}")

def handle_admin_callbacks(call):
    data = call.data
    chat_id = call.message.chat.id

    if data == "admin_count":
        bot.answer_callback_query(call.id, f"Total Users: {len(users)}")

    elif data == "admin_stats":
        global downloads
        downloads = load_data(DOWNLOAD_FILE, {"lite": 0, "seven": 0})
        msg = (f"📊 <b>Download Statistics</b>\n"
               f"𝙻𝙸𝚃𝙴: {downloads.get('lite', 0)}\n"
               f"𝚂𝙴𝚅𝙴𝙽: {downloads.get('seven', 0)}")
        try:
            bot.send_message(chat_id, msg, parse_mode='HTML')
        except:
            pass

    elif data == "admin_broadcast":
        msg = bot.send_message(chat_id, "📢 Send broadcast content:")
        bot.register_next_step_handler(msg, broadcast_message)

    elif data == "admin_maintenance":
        current = settings.get("maintenance", False)
        settings["maintenance"] = not current
        save_settings()
        status = "ON 🔴" if settings["maintenance"] else "OFF 🟢"
        bot.answer_callback_query(call.id, f"Maintenance mode is now {status}")
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        admin_panel(chat_id)

    elif data == "admin_ban_prompt":
        msg = bot.send_message(chat_id, "🚫 Send the User ID to ban:")
        bot.register_next_step_handler(msg, process_ban_id)

    elif data == "admin_unban_prompt":
        msg = bot.send_message(chat_id, "✅ Send the User ID to unban:")
        bot.register_next_step_handler(msg, process_unban_id)

def broadcast_message(message):
    if message.chat.id != ADMIN_ID:
        return

    sent_count = 0
    fail_count = 0
    
    status_msg = bot.send_message(ADMIN_ID, "⏳ Broadcasting started...")

    for user in users:
        try:
            bot.copy_message(int(user), ADMIN_ID, message.message_id)
            sent_count += 1
            time.sleep(0.05)  # Small delay to avoid rate limiting
        except Exception:
            fail_count += 1

    try:
        bot.edit_message_text(f"✅ Broadcast Finished!\nSuccess: {sent_count}\nFailed: {fail_count}", ADMIN_ID, status_msg.message_id)
    except:
        bot.send_message(ADMIN_ID, "Broadcast Finished.")

def process_ban_id(message):
    if message.chat.id != ADMIN_ID: return
    try:
        uid = int(message.text)
        banned.add(uid)
        save_banned()
        bot.send_message(ADMIN_ID, f"🚫 User {uid} has been banned.")
    except ValueError:
        bot.send_message(ADMIN_ID, "❌ Invalid ID.")

def process_unban_id(message):
    if message.chat.id != ADMIN_ID: return
    try:
        uid = int(message.text)
        if uid in banned:
            banned.remove(uid)
            save_banned()
            bot.send_message(ADMIN_ID, f"✅ User {uid} has been unbanned.")
        else:
            bot.send_message(ADMIN_ID, "User is not banned.")
    except ValueError:
        bot.send_message(ADMIN_ID, "❌ Invalid ID.")

# ---------------- QUICK COMMANDS ----------------
@bot.message_handler(commands=['ban'])
def ban_user_cmd(message):
    if message.chat.id == ADMIN_ID and message.reply_to_message:
        source_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        match = re.search(r'#ID_(\d+)', source_text)
        if match:
            uid = int(match.group(1))
            banned.add(uid)
            save_banned()
            bot.send_message(ADMIN_ID, f"🚫 User {uid} Banned")

@bot.message_handler(commands=['unban'])
def unban_user_cmd(message):
    if message.chat.id == ADMIN_ID:
        try:
            uid = int(message.text.split()[1])
            if uid in banned:
                banned.remove(uid)
                save_banned()
                bot.send_message(ADMIN_ID, f"✅ User {uid} Unbanned")
        except:
            pass

# ---------------- FIXED MAIN LOOP ----------------
print("🚀 Bot is starting...")
print("⚠️ Make sure no other instances of this bot are running!")

def start_bot():
    """Main bot loop with proper error handling"""
    retry_count = 0
    max_retries = 10
    
    while True:
        try:
            print("🟢 Bot is running...")
            # Use polling with proper settings
            bot.polling(none_stop=True, interval=1, timeout=30, skip_pending=True)
            
        except Exception as e:
            error_msg = str(e)
            
            # Handle 409 Conflict error specifically
            if "409" in error_msg and "Conflict" in error_msg:
                print("❌ ERROR: Another instance of this bot is already running!")
                print("🔍 Please check:")
                print("  1. Close any other Termux sessions running this bot")
                print("  2. Stop any webhooks: https://api.telegram.org/bot{TOKEN}/deleteWebhook")
                print("  3. Wait 30 seconds and restart")
                print("🔄 Attempting to stop other instances...")
                
                # Try to delete webhook to clear any hanging connections
                try:
                    requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
                    print("✅ Webhook deleted. Waiting 10 seconds...")
                    time.sleep(10)
                except:
                    pass
                    
                retry_count += 1
                if retry_count > max_retries:
                    print("❌ Max retries reached. Please manually stop other bot instances.")
                    break
                    
            elif "Remote end closed connection" in error_msg:
                print("🌐 Connection lost. Reconnecting...")
                retry_count = 0  # Reset retry count for connection issues
                time.sleep(5)
                
            else:
                print(f"❌ Unexpected error: {error_msg}")
                retry_count += 1
                if retry_count > max_retries:
                    print("❌ Too many errors. Exiting...")
                    break
                time.sleep(5)

# Start the bot with the improved main loop
if __name__ == "__main__":
    start_bot()
