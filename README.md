# Telegram File Downloader Bot

A powerful Telegram bot that downloads files from various sources with specialized support for YouTube videos and audio downloads.

## Features

- **Universal File Downloader** - Download files from any direct link
- **YouTube Support** - Smart detection and format selection
- **Audio Downloads** - Extract audio in multiple bitrates (128, 192, 320 kbps)
- **Video Downloads** - Multiple resolutions (360p, 480p, 720p)
- **Premium Features** - Support for 1080p+ downloads
- **Real-time Progress** - Animated progress indicators with download stats
- **Smart Error Handling** - Helpful error messages and automatic retries

## Installation

### Prerequisites

- Python 3.11 or higher
- FFmpeg
- Telegram Bot Token

### Setup

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/telegram-downloader-bot.git
cd telegram-downloader-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install FFmpeg:

**Windows:**
```bash
choco install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

4. Create `.env` file:
```env
BOT_TOKEN=your_telegram_bot_token_here
```

Get your bot token from [@BotFather](https://t.me/BotFather) on Telegram.

5. Setup YouTube cookies (required):
   - Install [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) extension
   - Go to YouTube.com
   - Export cookies and save as `cookies.txt` in project root

6. Run the bot:
```bash
python bot.py
```

## Usage

### Commands

- `/start` - Welcome message and bot information
- `/premium` - Information about premium features

### How to Use

1. Start a chat with your bot on Telegram
2. Send any link:
   - **YouTube links** → Choose audio or video format
   - **Direct file links** → Automatic download
3. Select quality options
4. Receive your file with progress updates

## Configuration

### Premium Users

Add Telegram user IDs to enable 1080p+ downloads:

```python
PREMIUM_USERS = {123456789, 987654321}
```

### Customization

Modify settings in `bot.py`:
- Download timeouts
- File size limits
- Quality options
- Progress update intervals

## Deployment

### Render.com

1. Push code to GitHub
2. Create new Background Worker on Render
3. Connect repository
4. Add environment variable: `BOT_TOKEN`
5. Deploy

### Railway.app

1. Push code to GitHub
2. Create new project from GitHub
3. Add environment variable: `BOT_TOKEN`
4. Deploy

## Troubleshooting

**Bot won't start:**
- Check `BOT_TOKEN` in `.env`
- Verify internet connection
- Ensure Python 3.11+ installed

**YouTube downloads fail:**
- Update `cookies.txt` (expires periodically)
- Verify FFmpeg installation
- Check YouTube link validity

**FFmpeg not found:**
- Run `ffmpeg -version` to verify installation
- Add FFmpeg to system PATH
- Set `FFMPEG_PATH` in `.env`

## Tech Stack

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube downloader
- [FFmpeg](https://ffmpeg.org/) - Media processing

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Disclaimer

This bot is for educational purposes. Users must comply with:
- YouTube's Terms of Service
- Copyright laws
- Telegram's Terms of Service

Download content only if you have the right to do so.

## Support

For issues or questions, open an [Issue](https://github.com/raviy00/telegram-downloader-bot/issues) on GitHub.


Made with Python
