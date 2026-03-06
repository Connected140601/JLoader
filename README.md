# JLoader - YouTube & Facebook Video Downloader

A modern, responsive web application for downloading videos from YouTube and Facebook platforms.

## Features

- **YouTube Downloader**: Download YouTube videos in multiple quality options
- **Facebook Downloader**: Download Facebook videos with ease
- **Modern UI**: Clean, responsive design using Tailwind CSS
- **Fast Processing**: Quick video information extraction
- **Multiple Formats**: Support for various video qualities
- **User-Friendly**: Simple interface with progress indicators

## Installation

1. Clone or download this project
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the Flask server:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Use the interface to:
   - Switch between YouTube and Facebook downloaders
   - Paste the video URL
   - Select video quality
   - Download the video

## Requirements

- Python 3.7 or higher
- Flask web framework
- yt-dlp for YouTube video extraction
- Modern web browser

## API Endpoints

- `POST /api/youtube` - Get YouTube video information
- `POST /api/facebook` - Get Facebook video information  
- `POST /api/download/youtube` - Download YouTube video
- `POST /api/download/facebook` - Download Facebook video

## Technical Details

- **Backend**: Flask with Python
- **Frontend**: HTML5, CSS3, JavaScript, Tailwind CSS
- **Video Processing**: yt-dlp library for YouTube
- **File Handling**: Temporary storage with automatic cleanup

## Note

This application is for educational and personal use only. Please respect copyright laws and terms of service of the platforms from which you download content.

## License

MIT License - Feel free to use and modify for your projects.
