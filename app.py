from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import requests
import re
import os
import tempfile
from urllib.parse import urlparse, parse_qs
import json

app = Flask(__name__)
CORS(app)

# Configuration
DOWNLOAD_FOLDER = os.environ.get('DOWNLOAD_FOLDER', tempfile.mkdtemp())
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

# Global progress storage
download_progress = {}

class MyLogger:
    def __init__(self, progress_id):
        self.progress_id = progress_id

    def debug(self, msg):
        # yt-dlp sends post-processing info via debug logs
        if self.progress_id:
            if '[Merger]' in msg:
                download_progress[self.progress_id] = {
                    'status': 'processing', 
                    'numeric_percent': 92, 
                    'msg': 'Merging video and audio...',
                    'speed_str': 'FFmpeg',
                    'downloaded_str': 'Processing',
                    'total_str': 'Merging'
                }
            elif '[VideoConvertor]' in msg:
                download_progress[self.progress_id] = {
                    'status': 'processing', 
                    'numeric_percent': 95, 
                    'msg': 'Converting to compatible MP4...',
                    'speed_str': 'FFmpeg',
                    'downloaded_str': 'Processing',
                    'total_str': 'Converting'
                }
            elif '[Metadata]' in msg:
                download_progress[self.progress_id] = {
                    'status': 'processing', 
                    'numeric_percent': 98, 
                    'msg': 'Applying metadata...',
                    'speed_str': 'FFmpeg',
                    'downloaded_str': 'Processing',
                    'total_str': 'Finalizing'
                }
        print(msg)

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)

def strip_ansi(text):
    if not text:
        return text
    # Strip ANSI escape sequences (terminal color codes)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def progress_hook(d, progress_id):
    if not progress_id:
        return
        
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        downloaded = d.get('downloaded_bytes', 0)
        
        # Calculate clean numeric percentage
        if total > 0:
            numeric_percent = (downloaded / total) * 100
        else:
            numeric_percent = 0

        p = {
            'status': 'downloading',
            'downloaded_bytes': downloaded,
            'total_bytes': total,
            'downloaded_str': format_bytes(downloaded),
            'total_str': format_bytes(total),
            'speed_str': strip_ansi(d.get('_speed_str', '0B/s')),
            'percent': strip_ansi(d.get('_percent_str', '0%')),
            'numeric_percent': numeric_percent,
            'eta': strip_ansi(d.get('_eta_str', '00:00')),
        }
        download_progress[progress_id] = p
    elif d['status'] == 'finished':
        download_progress[progress_id] = {
            'status': 'processing',
            'percent': '100%',
            'msg': 'Download complete. Finalizing...'
        }

def format_bytes(b):
    if b is None or b == 0: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if b < 1024: return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"

class YouTubeDownloader:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'nocheckcertificate': True,
            'no_color': True,
            'noplaylist': True,
            'socket_timeout': 15,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
    
    def get_video_info(self, url):
        # ... (rest of the code remains same)
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                video_id = info.get('id', '')
                title = info.get('title', 'Unknown Title')
                duration = self._format_duration(info.get('duration', 0))
                thumbnail = info.get('thumbnail', '')
                
                # Generate quality options based on available info
                # YouTube typically has these quality options
                formats = []
                
                # Check for specific format information
                raw_formats = info.get('formats', [])
                
                # Get unique heights from available formats
                heights = set()
                for fmt in raw_formats:
                    h = fmt.get('height')
                    if h and h >= 360:
                        heights.add(h)
                
                # If we have format info, use it
                if heights:
                    for h in sorted(heights, reverse=True)[:5]:
                        formats.append({
                            'quality': f"{h}p",
                            'size': 'Click to download',
                            'format_id': f'bestvideo[height={h}]',
                            'url': f'https://www.youtube.com/watch?v={video_id}'
                        })
                else:
                    # Default quality options
                    default_qualities = ['2160p', '1440p', '1080p', '720p', '480p', '360p']
                    for q in default_qualities:
                        formats.append({
                            'quality': q,
                            'size': 'Click to download',
                            'format_id': f'bestvideo[height<={q.replace("p", "")}]',
                            'url': f'https://www.youtube.com/watch?v={video_id}'
                        })
                
                return {
                    'title': title,
                    'duration': duration,
                    'thumbnail': thumbnail,
                    'videoId': video_id,
                    'formats': formats
                }
        except Exception as e:
            raise Exception(f"Failed to extract video info: {str(e)}")
    
    def download_video(self, video_id, quality, progress_id=None, download_type='mp4'):
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            if download_type == 'mp3':
                temp_id = f"{video_id}_audio_{os.getpid()}"
                final_filename = os.path.join(DOWNLOAD_FOLDER, f'{video_id}_audio.mp3')
                
                download_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{temp_id}.%(ext)s'),
                    'quiet': False,
                    'no_warnings': False,
                    'ffmpeg_location': '/opt/homebrew/bin/ffmpeg' if os.path.exists('/opt/homebrew/bin/ffmpeg') else 'ffmpeg',
                    'logger': MyLogger(progress_id),
                    'progress_hooks': [lambda d: progress_hook(d, progress_id)],
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }
            else:
                try:
                    height = int(quality.replace('p', ''))
                except ValueError:
                    height = 720
                
                temp_id = f"{video_id}_{height}_{os.getpid()}"
                final_filename = os.path.join(DOWNLOAD_FOLDER, f'{video_id}_{quality}.mp4')
                
                if os.path.exists(final_filename) and os.path.getsize(final_filename) > 1000:
                    return final_filename

                # Explicitly set ffmpeg location if found
                ffmpeg_path = '/opt/homebrew/bin/ffmpeg'
                if not os.path.exists(ffmpeg_path):
                    ffmpeg_path = 'ffmpeg' # fallback to PATH

                # Download options optimized for EXACT quality matching and MP4 compatibility
                # We strictly prioritize the requested height (e.g. 1080p)
                download_opts = {
                    'format': f'bestvideo[height={height}]+bestaudio/best[height={height}]/bestvideo[height<={height}]+bestaudio/best[height<={height}]/best',
                    'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{temp_id}.%(ext)s'),
                    'quiet': False,
                    'no_warnings': False,
                    'merge_output_format': 'mp4',
                    'ffmpeg_location': ffmpeg_path,
                    'logger': MyLogger(progress_id),
                    'progress_hooks': [lambda d: progress_hook(d, progress_id)],
                    'format_sort': [
                        f'res:{height}',
                        'codec:h264:m4a',
                        'ext:mp4:m4a',
                    ],
                    'postprocessors': [
                        {
                            'key': 'FFmpegVideoConvertor',
                            'preferedformat': 'mp4',
                        },
                        {
                            'key': 'FFmpegMetadata',
                            'add_metadata': True,
                        }
                    ],
                    'postprocessor_args': [
                        '-vcodec', 'libx264',
                        '-acodec', 'aac',
                        '-crf', '23',
                        '-preset', 'veryfast',
                        '-movflags', 'faststart'
                    ],
                }
            
            print(f"Starting download for {video_id} at {quality}. Temp ID: {temp_id}")
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([url])
            
            # Check for output file
            if download_type == 'mp3':
                temp_mp3 = os.path.join(DOWNLOAD_FOLDER, f'{temp_id}.mp3')
                if os.path.exists(temp_mp3):
                    if os.path.exists(final_filename):
                        os.remove(final_filename)
                    os.rename(temp_mp3, final_filename)
                    return final_filename
            else:
                temp_mp4 = os.path.join(DOWNLOAD_FOLDER, f'{temp_id}.mp4')
                if os.path.exists(temp_mp4):
                    if os.path.exists(final_filename):
                        os.remove(final_filename)
                    os.rename(temp_mp4, final_filename)
                    return final_filename
            
            # Fallback search
            for f in os.listdir(DOWNLOAD_FOLDER):
                if f.startswith(temp_id):
                    ext = '.mp3' if download_type == 'mp3' else '.mp4'
                    if f.endswith(ext):
                        source = os.path.join(DOWNLOAD_FOLDER, f)
                        if os.path.exists(final_filename):
                            os.remove(final_filename)
                        os.rename(source, final_filename)
                        return final_filename
            
            raise Exception(f"Downloaded file not found. Checked for {temp_id} in {DOWNLOAD_FOLDER}")
                    
        except Exception as e:
            print(f"Download error details: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Download failed: {str(e)}")
    
    def _format_size(self, size_bytes):
        if size_bytes == 0:
            return "Unknown size"
        
        size_mb = size_bytes / (1024 * 1024)
        if size_mb < 1:
            size_kb = size_bytes / 1024
            return f"{size_kb:.1f} KB"
        else:
            return f"{size_mb:.1f} MB"
    
    def _format_duration(self, duration_seconds):
        if duration_seconds == 0:
            return "Unknown duration"
        
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

class FacebookDownloader:
    def __init__(self):
        self.ydl_opts = {
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'nocheckcertificate': True,
            'no_color': True,
            'socket_timeout': 15,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
        # Explicitly set ffmpeg location if found
        self.ffmpeg_path = '/opt/homebrew/bin/ffmpeg'
        if not os.path.exists(self.ffmpeg_path):
            self.ffmpeg_path = 'ffmpeg' # fallback to PATH

    def get_video_info(self, url):
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                video_id = info.get('id', str(hash(url))[:10])
                title = info.get('title', 'Facebook Video')
                description = info.get('description', 'Video from Facebook')
                thumbnail = info.get('thumbnail', 'https://via.placeholder.com/320x180?text=Facebook+Video')
                
                formats = []
                # yt-dlp usually finds 'hd' and 'sd' for Facebook
                raw_formats = info.get('formats', [])
                
                seen_qualities = set()
                for fmt in raw_formats:
                    format_note = fmt.get('format_note') or fmt.get('quality_label')
                    if format_note and format_note not in seen_qualities:
                        formats.append({
                            'quality': format_note.upper(),
                            'format_id': fmt.get('format_id'),
                            'url': url
                        })
                        seen_qualities.add(format_note)
                
                if not formats:
                    formats = [
                        {'quality': 'HD', 'format_id': 'hd', 'url': url},
                        {'quality': 'SD', 'format_id': 'sd', 'url': url}
                    ]
                
                return {
                    'title': title,
                    'description': description,
                    'thumbnail': thumbnail,
                    'videoId': video_id,
                    'formats': formats
                }
        except Exception as e:
            print(f"Facebook info extraction error: {str(e)}")
            return {
                'title': 'Facebook Video',
                'description': 'Video from Facebook',
                'thumbnail': 'https://via.placeholder.com/320x180?text=Facebook+Video',
                'videoId': str(hash(url))[:10],
                'formats': [
                    {'quality': 'HD', 'format_id': 'hd', 'url': url},
                    {'quality': 'SD', 'format_id': 'sd', 'url': url}
                ]
            }

    def download_video(self, video_id, quality, progress_id=None, download_type='mp4'):
        try:
            # Reconstruct URL or use video_id if it's the full URL
            if 'facebook.com' in video_id or 'fb.watch' in video_id:
                url = video_id
                # Sanitize video_id for filename if it's a URL
                safe_id = re.sub(r'[^\w\-]', '_', video_id)[-20:]
            elif video_id.isdigit():
                url = f"https://www.facebook.com/watch?v={video_id}"
                safe_id = video_id
            else:
                # Handle cases where video_id might be part of a path (like Reels)
                url = f"https://www.facebook.com/reels/{video_id}" if 'reels' in video_id else f"https://www.facebook.com/watch?v={video_id}"
                safe_id = re.sub(r'[^\w\-]', '_', video_id)
            
            if download_type == 'mp3':
                temp_id = f"fb_{safe_id}_audio_{os.getpid()}"
                final_filename = os.path.join(DOWNLOAD_FOLDER, f'facebook_{safe_id}_audio.mp3')
                
                download_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{temp_id}.%(ext)s'),
                    'quiet': False,
                    'no_warnings': False,
                    'ffmpeg_location': self.ffmpeg_path,
                    'logger': MyLogger(progress_id),
                    'progress_hooks': [lambda d: progress_hook(d, progress_id)],
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }
            else:
                temp_id = f"fb_{safe_id}_{quality}_{os.getpid()}"
                final_filename = os.path.join(DOWNLOAD_FOLDER, f'facebook_{safe_id}_{quality}.mp4')
                
                if os.path.exists(final_filename) and os.path.getsize(final_filename) > 1000:
                    return final_filename

                download_opts = {
                    'format': 'bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[vcodec^=avc1][acodec^=mp4a]/best',
                    'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{temp_id}.%(ext)s'),
                    'quiet': False,
                    'no_warnings': False,
                    'merge_output_format': 'mp4',
                    'ffmpeg_location': self.ffmpeg_path,
                    'logger': MyLogger(progress_id),
                    'progress_hooks': [lambda d: progress_hook(d, progress_id)],
                    'format_sort': [
                        'res:1080' if quality.lower() == 'hd' else 'res:720',
                        'codec:h264:m4a',
                    ],
                    'postprocessors': [
                        {
                            'key': 'FFmpegVideoConvertor',
                            'preferedformat': 'mp4',
                        },
                        {
                            'key': 'FFmpegMetadata',
                            'add_metadata': True,
                        }
                    ],
                    'postprocessor_args': [
                        '-vcodec', 'libx264',
                        '-acodec', 'aac',
                        '-movflags', 'faststart'
                    ],
                }
            
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([url])
            
            if download_type == 'mp3':
                temp_mp3 = os.path.join(DOWNLOAD_FOLDER, f'{temp_id}.mp3')
                if os.path.exists(temp_mp3):
                    if os.path.exists(final_filename):
                        os.remove(final_filename)
                    os.rename(temp_mp3, final_filename)
                    return final_filename
            else:
                temp_mp4 = os.path.join(DOWNLOAD_FOLDER, f'{temp_id}.mp4')
                if os.path.exists(temp_mp4):
                    if os.path.exists(final_filename):
                        os.remove(final_filename)
                    os.rename(temp_mp4, final_filename)
                    return final_filename
            
            # Fallback
            for f in os.listdir(DOWNLOAD_FOLDER):
                if f.startswith(temp_id):
                    ext = '.mp3' if download_type == 'mp3' else '.mp4'
                    if f.endswith(ext):
                        source = os.path.join(DOWNLOAD_FOLDER, f)
                        if os.path.exists(final_filename):
                            os.remove(final_filename)
                        os.rename(source, final_filename)
                        return final_filename
            
            raise Exception("Facebook download failed - file not found")
                    
        except Exception as e:
            print(f"Facebook download error: {str(e)}")
            raise Exception(f"Facebook download failed: {str(e)}")

# Initialize downloaders
youtube_downloader = YouTubeDownloader()
facebook_downloader = FacebookDownloader()

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/script.js')
def script():
    return send_file('script.js')

@app.route('/favicon.svg')
def favicon():
    return send_file('favicon.svg')

@app.route('/api/youtube', methods=['POST'])
def youtube_info():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        info = youtube_downloader.get_video_info(url)
        return jsonify(info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/facebook', methods=['POST'])
def facebook_info():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        info = facebook_downloader.get_video_info(url)
        return jsonify(info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress/<progress_id>')
def get_progress(progress_id):
    progress = download_progress.get(progress_id, {'status': 'waiting', 'percent': '0%'})
    return jsonify(progress)

@app.route('/api/download/youtube', methods=['POST'])
def download_youtube():
    try:
        data = request.get_json()
        video_id = data.get('videoId')
        quality = data.get('quality')
        title = data.get('title', 'video')
        progress_id = data.get('progressId')
        download_type = data.get('type', 'mp4')
        
        if not video_id or (download_type == 'mp4' and not quality):
            return jsonify({'error': 'Video ID and quality are required'}), 400
        
        # Clean title for filename
        clean_title = re.sub(r'[^\w\-_\. ]', '_', title)
        ext = 'mp3' if download_type == 'mp3' else 'mp4'
        download_name = f"{clean_title}_{quality if download_type == 'mp4' else 'audio'}.{ext}"
        
        filename = youtube_downloader.download_video(video_id, quality, progress_id, download_type)
        return send_file(filename, as_attachment=True, download_name=download_name)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/facebook', methods=['POST'])
def download_facebook():
    try:
        data = request.get_json()
        video_id = data.get('videoId')
        quality = data.get('quality')
        title = data.get('title', 'facebook_video')
        progress_id = data.get('progressId')
        download_type = data.get('type', 'mp4')
        
        if not video_id or (download_type == 'mp4' and not quality):
            return jsonify({'error': 'Video ID and quality are required'}), 400
            
        # Clean title for filename
        clean_title = re.sub(r'[^\w\-_\. ]', '_', title)
        ext = 'mp3' if download_type == 'mp3' else 'mp4'
        download_name = f"{clean_title}_{quality if download_type == 'mp4' else 'audio'}.{ext}"
        
        filename = facebook_downloader.download_video(video_id, quality, progress_id, download_type)
        return send_file(filename, as_attachment=True, download_name=download_name)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Create download folder if it doesn't exist
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    
    # Get port from environment or default to 8080 for local development
    port = int(os.environ.get('PORT', 8080))
    
    print("Starting JLoader server...")
    print(f"Download folder: {DOWNLOAD_FOLDER}")
    print(f"Server will be available at: http://0.0.0.0:{port}")
    
    # Use appropriate server based on environment
    if os.environ.get('FLASK_ENV') == 'production':
        from gunicorn import app as gunicorn_app
        # In production, let Render handle the server startup
        app.run(host='0.0.0.0', port=port)
    else:
        app.run(debug=True, host='0.0.0.0', port=port)
