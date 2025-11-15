# Deploying LIZZY to Render

This guide explains how to deploy LIZZY 2.0 to Render.com.

## Prerequisites

1. A [Render.com](https://render.com) account
2. Your GitHub repository connected to Render
3. OpenAI API key
4. RAG buckets tar.gz file hosted at a publicly accessible URL

## Step 1: Get a Direct Download Link for RAG Buckets

Your RAG buckets are currently on Google Drive. You need to make them downloadable via a direct URL.

### Option A: Use a Direct Download Link Service
1. Go to your Google Drive file: `rag_buckets.tar.gz`
2. Make sure it's set to "Anyone with the link can view"
3. Use a service to convert the Google Drive link to a direct download URL:
   - https://sites.google.com/site/gdocs2direct/
   - Or manually construct: `https://drive.google.com/uc?export=download&id=FILE_ID`
   - Your file ID: `1aaWh7ZwXgo7ZvC3haH2zMP8pjlCvx5r0`
   - Direct URL: `https://drive.google.com/uc?export=download&id=1aaWh7ZwXgo7ZvC3haH2zMP8pjlCvx5r0`

### Option B: Host on GitHub Releases (Recommended for large files)
1. Create a new release in your GitHub repo
2. Upload `rag_buckets.tar.gz` as a release asset
3. Use the direct download URL from the release

### Option C: Use Alternative Storage
- Amazon S3
- Dropbox with direct link
- Any CDN or file hosting service

## Step 2: Set Up Render Service

### Using render.yaml (Automated)

1. Push the `render.yaml` and `build.sh` files to your repository
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click "New +" → "Blueprint"
4. Connect your GitHub repository
5. Render will automatically detect `render.yaml`

### Manual Setup

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository (`ejresearch/LIZZY`)
4. Configure:
   - **Name**: `lizzy` (or your preference)
   - **Runtime**: `Python 3`
   - **Build Command**: `bash build.sh`
   - **Start Command**: `python servers/landing_server.py`
   - **Plan**: Starter ($7/month) or higher

## Step 3: Configure Environment Variables

In your Render service settings, add these environment variables:

| Variable | Value | Required |
|----------|-------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | ✅ Yes |
| `RAG_BUCKETS_URL` | Direct download URL for rag_buckets.tar.gz | ✅ Yes |
| `COHERE_API_KEY` | Your Cohere API key (optional) | ❌ No |
| `PYTHON_VERSION` | `3.11.0` | ❌ No (recommended) |

### Example:
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
RAG_BUCKETS_URL=https://drive.google.com/uc?export=download&id=1aaWh7ZwXgo7ZvC3haH2zMP8pjlCvx5r0
COHERE_API_KEY=your-cohere-key (optional)
```

## Step 4: Deploy

1. Click "Create Web Service" (or "Apply" if using Blueprint)
2. Render will:
   - Clone your repository
   - Run `build.sh` (install deps, download buckets, extract)
   - Start the server
3. Monitor the build logs for any errors
4. Once deployed, your app will be available at: `https://lizzy-xxxx.onrender.com`

## Step 5: Verify Deployment

Once deployed, test these endpoints:

- **Landing Page**: `https://your-app.onrender.com/`
- **Health Check**: `https://your-app.onrender.com/api/health`
- **API Docs**: `https://your-app.onrender.com/docs`

## Troubleshooting

### Build Fails: "RAG_BUCKETS_URL not set"
- Make sure you added the `RAG_BUCKETS_URL` environment variable in Render settings
- Verify the URL is accessible (test with `curl -L URL` locally)

### Build Times Out
- The 412 MB tar.gz download might timeout on free tier
- Solutions:
  - Upgrade to a paid plan (faster build servers)
  - Host buckets on a faster CDN
  - Consider using persistent disk storage

### "Permission denied: build.sh"
- Make sure `build.sh` is executable:
  ```bash
  chmod +x build.sh
  git add build.sh
  git commit -m "Make build.sh executable"
  git push
  ```

### Application Crashes on Startup
- Check environment variables are set correctly
- Review logs in Render dashboard
- Verify buckets were extracted properly (check logs for "RAG buckets installed successfully")

## Important Notes

### Ephemeral Filesystem
Render uses an **ephemeral filesystem** - files written at runtime (like new projects) will be **lost on restart**.

For production, consider:
1. **Persistent Disk** (Render add-on, $1/GB/month)
2. **External Database** (PostgreSQL instead of SQLite)
3. **Object Storage** (S3 for project files)

### Cost Estimate
- **Starter Plan**: $7/month
- **Persistent Disk** (if needed): ~$10/month for 10GB
- **Total**: ~$17/month

## Next Steps

After deployment:
1. Test all modules (START, INTAKE, BRAINSTORM, WRITE, EXPORT)
2. Verify RAG buckets are working (check brainstorm queries)
3. Set up monitoring/alerts
4. Consider adding a custom domain

---

Need help? Check the [Render Docs](https://render.com/docs) or open an issue.
