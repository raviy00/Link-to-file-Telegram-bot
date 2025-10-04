import os
import re
import asyncio
import shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import yt_dlp
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables!")

PREMIUM_USERS = set()  # Store premium user IDs

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=3)

# Find FFmpeg location
def find_ffmpeg():
    """Find FFmpeg in system PATH or common locations"""
    # Check environment variable first
    env_path = os.getenv("FFMPEG_PATH")
    if env_path and os.path.exists(os.path.join(env_path, 'ffmpeg.exe')):
        return env_path
    
    # Try system PATH
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return os.path.dirname(ffmpeg_path)
    
    # Check common Windows locations
    common_paths = [
        r'C:\ProgramData\chocolatey\bin',
        r'C:\ffmpeg\bin',
        r'C:\Program Files\ffmpeg\bin',
        r'C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg\bin',
    ]
    
    for path in common_paths:
        if os.path.exists(os.path.join(path, 'ffmpeg.exe')):
            return path
    
    return None

FFMPEG_LOCATION = find_ffmpeg()
print(f"FFmpeg location: {FFMPEG_LOCATION}")

# YouTube URL pattern
YOUTUBE_PATTERN = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'

def is_youtube_url(url):
    """Check if URL is a YouTube link"""
    return re.search(YOUTUBE_PATTERN, url) is not None

def is_premium_user(user_id):
    """Check if user has premium access"""
    return user_id in PREMIUM_USERS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    await update.message.reply_text(
        "👋 Welcome to File Downloader Bot!\n\n"
        "📎 Send me any link and I'll download it for you.\n"
        "🎥 For YouTube links, I'll give you format options.\n\n"
        "💎 Premium features (1080p+) available!\n"
        "Use /premium to learn more."
    )

async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Premium information command"""
    await update.message.reply_text(
        "💎 Premium Features:\n\n"
        "• Download videos in 1080p, 1440p, 4K\n"
        "• Faster download speeds\n"
        "• No ads\n\n"
        "💰 Price: $5/month\n\n"
        "Contact @itzmeane to subscribe!"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming links"""
    url = update.message.text.strip()
    user_id = update.message.from_user.id
    
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            await update.message.reply_text("❌ Invalid URL. Please send a valid link.")
            return
    except:
        await update.message.reply_text("❌ Invalid URL. Please send a valid link.")
        return
    
    # Check if it's a YouTube link
    if is_youtube_url(url):
        # Store URL in user context
        context.user_data['url'] = url
        
        # Create keyboard for format selection
        keyboard = [
            [InlineKeyboardButton("🎵 Audio", callback_data="format_audio")],
            [InlineKeyboardButton("🎬 Video", callback_data="format_video")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎥 YouTube link detected!\n\n"
            "Please choose format:",
            reply_markup=reply_markup
        )
    else:
        # Download regular file
        await update.message.reply_text("⏬ Downloading file...")
        await download_regular_file(update, url)

async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle format selection callbacks"""
    query = update.callback_query
    await query.answer()
    
    url = context.user_data.get('url')
    if not url:
        await query.edit_message_text("❌ Error: URL not found. Please send the link again.")
        return
    
    if query.data == "format_audio":
        # Show audio bitrate options
        keyboard = [
            [InlineKeyboardButton("🎵 128 kbps", callback_data="audio_128")],
            [InlineKeyboardButton("🎵 192 kbps", callback_data="audio_192")],
            [InlineKeyboardButton("🎵 320 kbps", callback_data="audio_320")],
            [InlineKeyboardButton("◀️ Back", callback_data="back_to_format")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎵 Select audio quality:",
            reply_markup=reply_markup
        )
    
    elif query.data == "format_video":
        user_id = query.from_user.id
        
        # Basic quality options
        keyboard = [
            [InlineKeyboardButton("📱 360p", callback_data="video_360")],
            [InlineKeyboardButton("📺 480p", callback_data="video_480")],
            [InlineKeyboardButton("🖥️ 720p", callback_data="video_720")],
        ]
        
        # Add premium options if user is premium
        if is_premium_user(user_id):
            keyboard.append([InlineKeyboardButton("💎 1080p (Premium)", callback_data="video_1080")])
            keyboard.append([InlineKeyboardButton("💎 1440p (Premium)", callback_data="video_1440")])
        else:
            keyboard.append([InlineKeyboardButton("🔒 1080p+ (Premium Only)", callback_data="premium_required")])
        
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="back_to_format")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎬 Select video quality:",
            reply_markup=reply_markup
        )
    
    elif query.data == "back_to_format":
        keyboard = [
            [InlineKeyboardButton("🎵 Audio", callback_data="format_audio")],
            [InlineKeyboardButton("🎬 Video", callback_data="format_video")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎥 YouTube link detected!\n\n"
            "Please choose format:",
            reply_markup=reply_markup
        )
    
    elif query.data == "premium_required":
        await query.answer("💎 Premium subscription required for 1080p+", show_alert=True)
        await query.message.reply_text(
            "💎 Premium Required!\n\n"
            "Subscribe to access 1080p, 1440p, and 4K downloads.\n"
            "Use /premium for more information."
        )

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle download callbacks"""
    query = update.callback_query
    await query.answer()
    
    url = context.user_data.get('url')
    if not url:
        await query.edit_message_text("❌ Error: URL not found. Please send the link again.")
        return
    
    # Parse quality selection
    data = query.data
    
    if data.startswith("audio_"):
        bitrate = data.split("_")[1]
        await query.edit_message_text(f"⏬ Downloading audio ({bitrate} kbps)...")
        await download_youtube_audio(query.message, url, bitrate)
    
    elif data.startswith("video_"):
        resolution = data.split("_")[1]
        user_id = query.from_user.id
        
        # Check premium requirement for high resolutions
        if int(resolution) > 720 and not is_premium_user(user_id):
            await query.answer("💎 Premium subscription required!", show_alert=True)
            await query.message.reply_text(
                "💎 Premium Required!\n\n"
                "Subscribe to access this quality.\n"
                "Use /premium for more information."
            )
            return
        
        await query.edit_message_text(f"⏬ Downloading video ({resolution}p)...")
        await download_youtube_video(query.message, url, resolution)

async def download_youtube_audio(message, url, bitrate):
    """Download YouTube video as audio"""
    progress_msg = None
    last_progress = ""
    
    try:
        # Send initial progress message
        progress_msg = await message.reply_text("🔍 Analyzing video...")
        
        progress_states = {
            'downloading': [],
            'processing': False
        }
        
        def progress_hook(d):
            """Progress callback for yt-dlp"""
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', '0%').strip()
                speed = d.get('_speed_str', 'N/A').strip()
                eta = d.get('_eta_str', 'N/A').strip()
                progress_states['downloading'] = [percent, speed, eta]
            elif d['status'] == 'finished':
                progress_states['processing'] = True
        
        def download_audio():
            """Blocking download operation"""
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': bitrate,
                }],
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'cookiefile': 'cookies.txt',
                'progress_hooks': [progress_hook],
                'socket_timeout': 60,
                'retries': 5,
            }
            
            # Add FFmpeg location if found
            if FFMPEG_LOCATION:
                ydl_opts['ffmpeg_location'] = FFMPEG_LOCATION
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                audio_file = filename.rsplit('.', 1)[0] + '.mp3'
                return audio_file, info
        
        # Run download in thread pool
        loop = asyncio.get_event_loop()
        download_task = loop.run_in_executor(executor, download_audio)
        
        # Enhanced progress animations
        download_frames = ['📥', '📥▪', '📥▪▪', '📥▪▪▪', '📥▪▪▪▪', '📥▪▪▪▪▪']
        processing_frames = ['🎵', '🎵♪', '🎵♪♫', '🎵♪♫♪', '🎵♪♫', '🎵♪']
        spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        progress_bars = ['▱▱▱▱▱▱▱▱▱▱', '▰▱▱▱▱▱▱▱▱▱', '▰▰▱▱▱▱▱▱▱▱', '▰▰▰▱▱▱▱▱▱▱', 
                        '▰▰▰▰▱▱▱▱▱▱', '▰▰▰▰▰▱▱▱▱▱', '▰▰▰▰▰▰▱▱▱▱', '▰▰▰▰▰▰▰▱▱▱',
                        '▰▰▰▰▰▰▰▰▱▱', '▰▰▰▰▰▰▰▰▰▱', '▰▰▰▰▰▰▰▰▰▰']
        
        frame_idx = 0
        last_update_time = 0
        
        # Update progress every 1.5 seconds
        while not download_task.done():
            await asyncio.sleep(1.5)
            
            current_time = loop.time()
            if current_time - last_update_time >= 1.5:
                try:
                    # Build animated progress message
                    if progress_states['processing']:
                        spinner_char = spinner[frame_idx % len(spinner)]
                        music_icon = processing_frames[frame_idx % len(processing_frames)]
                        new_progress = (
                            f"{music_icon} Converting to MP3...\n\n"
                            f"{spinner_char} Processing audio track\n"
                            f"🎧 Quality: {bitrate} kbps\n"
                            f"⚙️ Using FFmpeg encoder"
                        )
                    elif progress_states['downloading']:
                        percent, speed, eta = progress_states['downloading']
                        
                        # Parse percentage for progress bar
                        try:
                            percent_num = float(percent.replace('%', ''))
                            bar_idx = min(int(percent_num / 10), 10)
                            progress_bar = progress_bars[bar_idx]
                        except:
                            progress_bar = progress_bars[0]
                        
                        download_icon = download_frames[frame_idx % len(download_frames)]
                        new_progress = (
                            f"{download_icon} Downloading Audio\n\n"
                            f"📊 {progress_bar} {percent}\n"
                            f"⚡ Speed: {speed}\n"
                            f"⏱️ ETA: {eta}\n"
                            f"🎵 Quality: {bitrate} kbps"
                        )
                    else:
                        spinner_char = spinner[frame_idx % len(spinner)]
                        new_progress = (
                            f"{spinner_char} Initializing download...\n\n"
                            f"🔍 Fetching video information\n"
                            f"🌐 Connecting to YouTube\n"
                            f"🎵 Target: {bitrate} kbps MP3"
                        )
                    
                    # Update only if changed
                    if new_progress != last_progress:
                        await progress_msg.edit_text(new_progress)
                        last_progress = new_progress
                    
                    frame_idx += 1
                    last_update_time = current_time
                except:
                    pass
        
        # Get result with 15 minute timeout
        audio_file, info = await asyncio.wait_for(download_task, timeout=900)
        
        # Check file size
        file_size = os.path.getsize(audio_file)
        size_mb = file_size / (1024 * 1024)
        
        if file_size > 50 * 1024 * 1024:
            os.remove(audio_file)
            await progress_msg.edit_text(
                f"❌ File Too Large\n\n"
                f"📦 Size: {size_mb:.1f}MB\n"
                f"⚠️ Limit: 50MB\n\n"
                f"💡 Try a shorter video"
            )
            return
        
        # Upload progress with animation
        upload_frames = ['📤', '📤▫', '📤▫▫', '📤▫▫▫', '📤▫▫▫▫', '📤▫▫▫▫▫']
        for i in range(3):
            upload_icon = upload_frames[i % len(upload_frames)]
            await progress_msg.edit_text(
                f"{upload_icon} Uploading to Telegram\n\n"
                f"📦 Size: {size_mb:.1f}MB\n"
                f"🎵 Format: MP3 ({bitrate} kbps)\n"
                f"⏳ Please wait..."
            )
            await asyncio.sleep(0.5)
        
        # Send the audio file
        with open(audio_file, 'rb') as audio:
            await message.reply_audio(
                audio=audio,
                title=info.get('title', 'Audio')[:100],
                performer=info.get('uploader', 'Unknown')[:100],
                duration=int(info.get('duration', 0)),
                read_timeout=120,
                write_timeout=120
            )
        
        # Clean up
        os.remove(audio_file)
        
        # Success message with animation
        await progress_msg.edit_text(
            f"✅ Download Complete!\n\n"
            f"🎵 {info.get('title', 'Audio')[:50]}\n"
            f"📦 {size_mb:.1f}MB • {bitrate} kbps"
        )
        await asyncio.sleep(3)
        await progress_msg.delete()
        
    except asyncio.TimeoutError:
        if progress_msg:
            await progress_msg.edit_text(
                "⏱️ Timeout Error\n\n"
                "❌ Download took too long (>15 min)\n"
                "💡 Try a shorter video"
            )
    except Exception as e:
        error_msg = str(e).replace('[0;31m', '').replace('[0m', '')[:300]
        if 'ffmpeg' in error_msg.lower():
            error_msg = (
                "❌ FFmpeg Not Found\n\n"
                "Please install FFmpeg:\n"
                "choco install ffmpeg"
            )
        if progress_msg:
            await progress_msg.edit_text(f"❌ Error\n\n{error_msg}")
        else:
            await message.reply_text(f"❌ Error\n\n{error_msg}")

async def download_youtube_video(message, url, resolution):
    """Download YouTube video"""
    progress_msg = None
    last_progress = ""
    
    try:
        # Send initial progress message
        progress_msg = await message.reply_text("🔍 Analyzing video...")
        
        progress_states = {
            'downloading': [],
            'processing': False
        }
        
        def progress_hook(d):
            """Progress callback for yt-dlp"""
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', '0%').strip()
                speed = d.get('_speed_str', 'N/A').strip()
                eta = d.get('_eta_str', 'N/A').strip()
                progress_states['downloading'] = [percent, speed, eta]
            elif d['status'] == 'finished':
                progress_states['processing'] = True
        
        def download_video():
            """Blocking download operation"""
            ydl_opts = {
                'format': f'bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]',
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'cookiefile': 'cookies.txt',
                'progress_hooks': [progress_hook],
                'socket_timeout': 60,
                'retries': 5,
            }
            
            # Add FFmpeg location if found
            if FFMPEG_LOCATION:
                ydl_opts['ffmpeg_location'] = FFMPEG_LOCATION
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return filename, info
        
        # Run download in thread pool
        loop = asyncio.get_event_loop()
        download_task = loop.run_in_executor(executor, download_video)
        
        # Enhanced progress animations
        download_frames = ['📥', '📥▪', '📥▪▪', '📥▪▪▪', '📥▪▪▪▪', '📥▪▪▪▪▪']
        processing_frames = ['🎬', '🎬🎞️', '🎬🎞️📹', '🎬🎞️', '🎬']
        spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        progress_bars = ['▱▱▱▱▱▱▱▱▱▱', '▰▱▱▱▱▱▱▱▱▱', '▰▰▱▱▱▱▱▱▱▱', '▰▰▰▱▱▱▱▱▱▱', 
                        '▰▰▰▰▱▱▱▱▱▱', '▰▰▰▰▰▱▱▱▱▱', '▰▰▰▰▰▰▱▱▱▱', '▰▰▰▰▰▰▰▱▱▱',
                        '▰▰▰▰▰▰▰▰▱▱', '▰▰▰▰▰▰▰▰▰▱', '▰▰▰▰▰▰▰▰▰▰']
        
        frame_idx = 0
        last_update_time = 0
        
        # Update progress every 1.5 seconds
        while not download_task.done():
            await asyncio.sleep(1.5)
            
            current_time = loop.time()
            if current_time - last_update_time >= 1.5:
                try:
                    # Build animated progress message
                    if progress_states['processing']:
                        spinner_char = spinner[frame_idx % len(spinner)]
                        video_icon = processing_frames[frame_idx % len(processing_frames)]
                        new_progress = (
                            f"{video_icon} Processing Video...\n\n"
                            f"{spinner_char} Merging video & audio\n"
                            f"🎥 Quality: {resolution}p\n"
                            f"⚙️ Using FFmpeg encoder"
                        )
                    elif progress_states['downloading']:
                        percent, speed, eta = progress_states['downloading']
                        
                        # Parse percentage for progress bar
                        try:
                            percent_num = float(percent.replace('%', ''))
                            bar_idx = min(int(percent_num / 10), 10)
                            progress_bar = progress_bars[bar_idx]
                        except:
                            progress_bar = progress_bars[0]
                        
                        download_icon = download_frames[frame_idx % len(download_frames)]
                        new_progress = (
                            f"{download_icon} Downloading Video\n\n"
                            f"📊 {progress_bar} {percent}\n"
                            f"⚡ Speed: {speed}\n"
                            f"⏱️ ETA: {eta}\n"
                            f"🎥 Quality: {resolution}p"
                        )
                    else:
                        spinner_char = spinner[frame_idx % len(spinner)]
                        new_progress = (
                            f"{spinner_char} Initializing download...\n\n"
                            f"🔍 Fetching video information\n"
                            f"🌐 Connecting to YouTube\n"
                            f"🎥 Target: {resolution}p MP4"
                        )
                    
                    # Update only if changed
                    if new_progress != last_progress:
                        await progress_msg.edit_text(new_progress)
                        last_progress = new_progress
                    
                    frame_idx += 1
                    last_update_time = current_time
                except:
                    pass
        
        # Get result with 15 minute timeout
        filename, info = await asyncio.wait_for(download_task, timeout=900)
        
        # Check file size
        file_size = os.path.getsize(filename)
        size_mb = file_size / (1024 * 1024)
        
        if file_size > 50 * 1024 * 1024:
            os.remove(filename)
            await progress_msg.edit_text(
                f"❌ File Too Large\n\n"
                f"📦 Size: {size_mb:.1f}MB\n"
                f"⚠️ Limit: 50MB\n\n"
                f"💡 Try lower quality:\n"
                f"• 360p for longer videos\n"
                f"• 480p for medium videos\n"
                f"• 720p for short clips"
            )
            return
        
        # Upload progress with animation
        upload_frames = ['📤', '📤▫', '📤▫▫', '📤▫▫▫', '📤▫▫▫▫', '📤▫▫▫▫▫']
        for i in range(3):
            upload_icon = upload_frames[i % len(upload_frames)]
            await progress_msg.edit_text(
                f"{upload_icon} Uploading to Telegram\n\n"
                f"📦 Size: {size_mb:.1f}MB\n"
                f"🎥 Format: MP4 ({resolution}p)\n"
                f"⏳ Please wait..."
            )
            await asyncio.sleep(0.5)
        
        # Send the video file
        with open(filename, 'rb') as video:
            await message.reply_video(
                video=video,
                caption=info.get('title', 'Video')[:200],
                duration=int(info.get('duration', 0)),
                width=int(info.get('width', 0)),
                height=int(info.get('height', 0)),
                supports_streaming=True,
                read_timeout=120,
                write_timeout=120
            )
        
        # Clean up
        os.remove(filename)
        
        # Success message
        await progress_msg.edit_text(
            f"✅ Download Complete!\n\n"
            f"🎥 {info.get('title', 'Video')[:50]}\n"
            f"📦 {size_mb:.1f}MB • {resolution}p"
        )
        await asyncio.sleep(3)
        await progress_msg.delete()
        
    except asyncio.TimeoutError:
        if progress_msg:
            await progress_msg.edit_text(
                "⏱️ Timeout Error\n\n"
                "❌ Download took too long (>15 min)\n"
                "💡 Try lower quality or shorter video"
            )
    except Exception as e:
        error_msg = str(e).replace('[0;31m', '').replace('[0m', '')[:300]
        if 'ffmpeg' in error_msg.lower():
            error_msg = (
                "❌ FFmpeg Not Found\n\n"
                "Please install FFmpeg:\n"
                "choco install ffmpeg"
            )
        if progress_msg:
            await progress_msg.edit_text(f"❌ Error\n\n{error_msg}")
        else:
            await message.reply_text(f"❌ Error\n\n{error_msg}")
        if progress_msg:
            await progress_msg.edit_text(f"❌ Error: {error_msg}")
        else:
            await message.reply_text(f"❌ Error: {error_msg}")

async def download_regular_file(update: Update, url):
    """Download regular files from links"""
    progress_msg = None
    last_progress = ""
    
    try:
        progress_msg = await update.message.reply_text("🔍 Analyzing file...")
        
        def download_file():
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            # Get filename
            filename = url.split('/')[-1] or 'downloaded_file'
            if 'Content-Disposition' in response.headers:
                content_disp = response.headers['Content-Disposition']
                if 'filename=' in content_disp:
                    filename = content_disp.split('filename=')[1].strip('"')
            
            filepath = f"downloads/{filename}"
            os.makedirs('downloads', exist_ok=True)
            
            # Get file size if available
            total_size = int(response.headers.get('content-length', 0))
            
            # Download file with progress
            downloaded = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
            
            return filepath, filename, total_size
        
        # Start download with animated progress
        loop = asyncio.get_event_loop()
        download_task = loop.run_in_executor(executor, download_file)
        
        # Progress animations
        download_frames = ['📥', '📥▪', '📥▪▪', '📥▪▪▪', '📥▪▪▪▪', '📥▪▪▪▪▪']
        spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        frame_idx = 0
        last_update_time = 0
        
        # Update progress every 1.5 seconds
        while not download_task.done():
            await asyncio.sleep(1.5)
            
            current_time = loop.time()
            if current_time - last_update_time >= 1.5:
                try:
                    spinner_char = spinner[frame_idx % len(spinner)]
                    download_icon = download_frames[frame_idx % len(download_frames)]
                    new_progress = (
                        f"{download_icon} Downloading File\n\n"
                        f"{spinner_char} Fetching from server\n"
                        f"🌐 Connecting...\n"
                        f"⏳ Please wait..."
                    )
                    
                    if new_progress != last_progress:
                        await progress_msg.edit_text(new_progress)
                        last_progress = new_progress
                    
                    frame_idx += 1
                    last_update_time = current_time
                except:
                    pass
        
        # Get result with 5 minute timeout
        filepath, filename, total_size = await asyncio.wait_for(
            download_task,
            timeout=300
        )
        
        # Check file size
        file_size = os.path.getsize(filepath)
        size_mb = file_size / (1024 * 1024)
        
        if file_size > 50 * 1024 * 1024:
            os.remove(filepath)
            await progress_msg.edit_text(
                f"❌ File Too Large\n\n"
                f"📦 Size: {size_mb:.1f}MB\n"
                f"⚠️ Limit: 50MB\n\n"
                f"💡 Telegram has a 50MB file size limit"
            )
            return
        
        # Upload animation
        upload_frames = ['📤', '📤▫', '📤▫▫', '📤▫▫▫', '📤▫▫▫▫', '📤▫▫▫▫▫']
        for i in range(3):
            upload_icon = upload_frames[i % len(upload_frames)]
            await progress_msg.edit_text(
                f"{upload_icon} Uploading to Telegram\n\n"
                f"📦 Size: {size_mb:.1f}MB\n"
                f"📄 File: {filename[:30]}\n"
                f"⏳ Please wait..."
            )
            await asyncio.sleep(0.5)
        
        # Send file
        with open(filepath, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=filename,
                read_timeout=120,
                write_timeout=120
            )
        
        # Clean up
        os.remove(filepath)
        
        # Success message
        await progress_msg.edit_text(
            f"✅ Download Complete!\n\n"
            f"📄 {filename[:40]}\n"
            f"📦 {size_mb:.1f}MB"
        )
        await asyncio.sleep(3)
        await progress_msg.delete()
        
    except asyncio.TimeoutError:
        if progress_msg:
            await progress_msg.edit_text(
                "⏱️ Timeout Error\n\n"
                "❌ Download took too long (>5 min)\n"
                "💡 File may be too large or slow"
            )
    except Exception as e:
        error_msg = str(e)[:300]
        if progress_msg:
            await progress_msg.edit_text(
                f"❌ Download Error\n\n"
                f"{error_msg}"
            )
        else:
            await update.message.reply_text(
                f"❌ Download Error\n\n"
                f"{error_msg}"
            )

def main():
    """Start the bot"""
    # Create downloads directory
    os.makedirs('downloads', exist_ok=True)
    
    # Create application with proxy support if needed
    builder = Application.builder().token(BOT_TOKEN)
    
    # Increase timeouts
    builder.read_timeout(30).write_timeout(30).connect_timeout(30)
    
    app = builder.build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium_info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(format_callback, pattern="^format_"))
    app.add_handler(CallbackQueryHandler(format_callback, pattern="^back_to_format$"))
    app.add_handler(CallbackQueryHandler(format_callback, pattern="^premium_required$"))
    app.add_handler(CallbackQueryHandler(download_callback, pattern="^(audio_|video_)"))
    
    # Start bot
    print("Bot started...")
    app.run_polling()

if __name__ == '__main__':
    main()