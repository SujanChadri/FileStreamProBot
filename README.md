
# 📦 Telegram File Stream Bot Configuration

A simple configuration module for linking and managing a Telegram File Stream Bot.  
This script loads all required environment variables to set up your bot seamlessly using the **Telegram Bot API** and **Pyrogram** (or similar frameworks).

---

## 🧠 Overview

This script uses Python’s built-in `os` and `dotenv` libraries to load configuration values from environment variables (or a `.env` file).  
It defines a `Var` class containing all important bot configuration parameters.

---

## ⚙️ Requirements

- Python 3.8 or higher  
- Required packages:
  ```bash
  pip install python-dotenv
````

* A `.env` file or environment variables with the following values (see below)

---

## 📁 Environment Variables

Below are the environment variables used by the bot:

| Variable Name             | Description                                                  | Required | Default / Example                                |
| ------------------------- | ------------------------------------------------------------ | -------- | ------------------------------------------------ |
| `API_ID`                  | Telegram API ID                                              | ✅        | `28405636`                                       |
| `API_HASH`                | Telegram API Hash                                            | ✅        | `52b6dfbaeea988407006cefbea7c2e04`               |
| `BOT_TOKEN`               | Telegram Bot Token from [@BotFather](https://t.me/BotFather) | ✅        | `7902407945:AAFCJidyZ1ELUnQuR41iv6QJkslc8j9SzRI` |
| `name`                    | Bot name (optional)                                          | ❌        | `FileStreamBot`                                  |
| `SLEEP_THRESHOLD`         | Delay threshold for async tasks                              | ❌        | `60`                                             |
| `WORKERS`                 | Number of concurrent workers                                 | ❌        | `4`                                              |
| `BIN_CHANNEL`             | Channel ID to store files                                    | ✅        | `-1002044705664`                                 |
| `PORT`                    | Web server port                                              | ❌        | `3000`                                           |
| `WEB_SERVER_BIND_ADDRESS` | Web server bind address                                      | ❌        | `0.0.0.0`                                        |
| `PING_INTERVAL`           | Ping interval (in seconds)                                   | ❌        | `1200`                                           |
| `OWNER_ID`                | Telegram user ID(s) of bot owner(s)                          | ✅        | `6713397633`                                     |
| `NO_PORT`                 | Disable port binding                                         | ❌        | `False`                                          |
| `APP_NAME`                | Heroku app name (for deployment)                             | ❌        | `None`                                           |
| `OWNER_USERNAME`          | Bot owner’s Telegram username                                | ✅        | `shivamnox`                                      |
| `FQDN`                    | Fully qualified domain name                                  | ❌        | `0.0.0.0:3000`                                   |
| `HAS_SSL`                 | Enable SSL for bot URL                                       | ❌        | `False`                                          |
| `SERVER_URL`              | Your Serer Url                                               | ✅        | `https://your-app-name.com`                      |
| `DATABASE_URL`            | MongoDB connection string                                    | ✅        | `mongodb+srv://...`                              |
| `UPDATES_CHANNEL`         | Telegram updates/news channel username                       | ✅        | `hivajoyweb`                                     |
| `BANNED_CHANNELS`         | List of banned channel IDs                                   | ❌        | `-1001362659779`                                 |

---

## ⚙️ Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/yourusername/filestreambot.git
cd filestreambot
````

### 2️⃣ Create a Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Install Dependencies

```bash
pip3 install -r requirements.txt
```

---

## 🧾 Configuration

Create a `.env` file in the project root directory and fill it with your credentials:

```env
API_ID=29876636
API_HASH=52b6dfbaee00000000cefbea7c2e04
BOT_TOKEN=your_bot_token_here
BIN_CHANNEL=-1002044705664
DATABASE_URL=your_mongodb_connection_url
SERVER_URL=https://your-server-url.com
OWNER_ID=Owner_id
OWNER_USERNAME=Username
UPDATES_CHANNEL=channel_username
```

> ⚠️ **Important:**
>
> * Replace `your_bot_token_here` and other credentials with your actual values.
> * Never share your bot token or database credentials publicly.

---

## 🚀 Running the Bot

To start the bot, run:

```bash
python3 -m Sujan.__main__
```

If everything is configured correctly, your bot will connect to Telegram and start running.

---

## 💡 Deployment Options

You can deploy this bot on:

* **Render**
* **Heroku**
* **Railway**
* **VPS / Local Machine**

### Heroku Example

1. Push your code to a GitHub repository.
2. Create a new Heroku app.
3. Go to **Settings → Config Vars** and add all required variables.
4. Deploy the app.

---

## 📝 License

This project is for educational and personal use.
Please use your own API keys and database credentials.
Redistribution of private tokens is not allowed.

## 🔊 Dual / Multi Audio

The bot auto-detects every audio track inside a file (Japanese, Hindi, English, Tamil, Telugu, Kannada, Malayalam, Bengali, Korean and many more).

- Detected languages are shown in the generated link message (e.g. `Dual Audio (2) : Hindi, English`).
- The watch page shows an **Audio Track** dropdown to switch language while playing.
- Detection uses `ffprobe`; if it is missing it falls back to reading the filename.

**Requirement:** install ffmpeg on the server.
- Heroku: add the buildpack `heroku-community/apt` (the included `Aptfile` installs ffmpeg).
- VPS/Docker: `apt install -y ffmpeg`.
- Endpoints added: `GET /api/audio/<id>?hash=<hash>` (track list) and `GET /track/<n>/<hash><id>` (stream one selected audio track).
