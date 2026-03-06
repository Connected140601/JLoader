# Deploy to Render

This guide will help you deploy your video downloader application to Render.

## Prerequisites
- A Render account (free tier available)
- GitHub repository with your code

## Step 1: Push to GitHub

1. Initialize git repository if not already done:
```bash
git init
git add .
git commit -m "Initial commit - Video downloader app"
```

2. Create a new repository on GitHub
3. Push your code:
```bash
git remote add origin https://github.com/yourusername/video-downloader.git
git branch -M main
git push -u origin main
```

## Step 2: Deploy to Render

1. Go to [render.com](https://render.com) and sign in
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: video-downloader (or your preferred name)
   - **Environment**: Python 3
   - **Branch**: main
   - **Root Directory**: (leave empty if files are in root)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
   - **Instance Type**: Free (to start)

5. Add Environment Variables:
   - `FLASK_ENV`: `production`
   - `PORT`: `10000`
   - `DOWNLOAD_FOLDER`: `/tmp/downloads`

6. Click "Create Web Service"

## Step 3: Configure Health Check

Render will automatically use the `/health` endpoint for health checks. This endpoint is already implemented in your app.

## Step 4: Test Your Deployment

Once deployed, your app will be available at:
`https://your-app-name.onrender.com`

Test the following:
- Home page loads correctly
- YouTube video info extraction works
- Facebook video info extraction works
- Download functionality works
- Health check endpoint: `https://your-app-name.onrender.com/health`

## Important Notes

### Storage Limitations
- Render's free tier uses ephemeral storage
- Downloaded files are stored in `/tmp` and may be cleaned up
- Consider implementing a cleanup mechanism for old files

### Performance
- Free tier has limited resources
- Video downloads may timeout for large files
- Consider upgrading to paid plan for production use

### Security
- Your app is publicly accessible
- Consider adding rate limiting
- Monitor for abuse

## Troubleshooting

### Common Issues

1. **Build fails**: Check requirements.txt for correct package versions
2. **App won't start**: Check logs for missing dependencies or port conflicts
3. **Downloads fail**: Check if yt-dlp can access the video URLs
4. **Storage issues**: Check if `/tmp` directory has sufficient space

### Monitoring

Check your Render dashboard for:
- Build logs
- Application logs
- Resource usage
- Health check status

## Scaling

If you need to scale:
1. Upgrade to paid instance types
2. Add Redis for progress tracking (instead of in-memory)
3. Add persistent storage for downloaded files
4. Implement proper cleanup and monitoring

## Alternative Deployment Options

If Render doesn't work for you, consider:
- Heroku (similar to Render)
- Vercel (for static sites)
- DigitalOcean App Platform
- AWS Elastic Beanstalk
- Self-hosted VPS
