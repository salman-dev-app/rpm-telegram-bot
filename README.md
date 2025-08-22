# RPM URL Uploader Bot (Multi-User Edition)

A powerful and stylish Telegram bot to upload files from direct download links to RPM Share. This bot is designed for multiple users, allowing each user to set their own RPM Share API Key and custom domain for generated links. It includes a full-featured admin panel for easy management.

![Bot Banner](https://i.ibb.co/9vP0YyF/bot-banner.png) 
*(Note: You can replace this image with your own banner)*

## ✨ Features

- **Multi-User System:** Each user can set and use their own RPM Share API key.
- **Custom Domains:** Users can define their own base URL for the final embed links.
- **Direct URL Uploading:** Just send a link, and the bot handles the rest.
- **Admin Panel:** Full control over the bot with special commands.
- **Broadcast System:** Send messages to all users of the bot.
- **User Statistics:** Keep track of how many users are using your bot.
- **Persistent Storage:** User data is saved in a JSON file, so it's not lost on restart.

## 🚀 Deployment

This bot is designed to be deployed easily on a cloud platform like **Railway.app**.

### 1. Fork this Repository
First, fork this repository to your own GitHub account.

### 2. Deploy on Railway
- Create a new project on [Railway.app](https://railway.app) and deploy from your forked GitHub repo.

### 3. Add Environment Variables
Go to your project's "Variables" tab and add the following:

- `BOT_TOKEN`: Your bot token from @BotFather.
- `ADMIN_ID`: Your personal Telegram User ID (get from @userinfobot).
- `DEFAULT_DOMAIN`: (Optional) The default URL to use if a user doesn't set a custom one (e.g., `https://aniwavelite.rpmlive.online/`).

### 4. Set the Start Command
- Go to the "Settings" tab of your service.
- In the "Deploy" section, set the **Start Command** to:
  ```  python main.py
  ```
Your bot is now live!

## 🤖 Bot Commands

### For All Users
- `/start` - Starts the bot.
- `/help` - Shows a detailed help message.
- `/setkey <api_key>` - Saves your personal RPM Share API Key.
  - *Example:* `/setkey 123456abcdefg`
- `/setdomain <your_url>` - Sets your personal base URL for links.
  - *Example:* `/setdomain https://my-awesome-site.com/`
- `/my_settings` - Shows your currently saved API Key and domain URL.

### 👑 For Admins Only
- `/stats` - Shows the total number of users.
- `/broadcast <message>` - Sends a message to all registered users.
  - *Example:* `/broadcast The bot will be under maintenance for 10 minutes.`

##  credit

- **Owner & Developer:** MD SALMAN

---
