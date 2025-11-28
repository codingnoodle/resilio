# 🚀 Cloud Deployment Guide for Resilio

## Dockerfile Review & Cloud Deployment

### ✅ Current Dockerfile Status
The Dockerfile is **ready for cloud deployment** with the following configurations:

- **Base Image**: Python 3.9-slim (lightweight, secure)
- **Port**: 8080 (standard for Google Cloud Run)
- **Address**: 0.0.0.0 (allows external connections)
- **Optimizations**: Layer caching, no-cache pip installs

### 🔧 Improvements Made

1. **Added `.dockerignore`**: Excludes `venv/`, `__pycache__/`, and other unnecessary files
2. **Enhanced Dockerfile**: Added health checks and environment variables
3. **Fixed Code Issues**: 
   - Fixed `AuditReport` class syntax error
   - Updated `pydantic` import for compatibility
   - Fixed auditor agent recursion issue

### 📦 Deployment Options

#### Option 1: Google Cloud Run (Recommended)

```bash
# Build the container
docker build -t resilio-app .

# Test locally
docker run -p 8080:8080 \
  -e GOOGLE_API_KEY="your_key" \
  -e TAVILY_API_KEY="your_key" \
  resilio-app

# Push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/resilio-app

# Deploy to Cloud Run
gcloud run deploy resilio-app \
  --image gcr.io/PROJECT_ID/resilio-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY="your_key",TAVILY_API_KEY="your_key" \
  --port 8080
```

#### Option 2: Docker Hub + Any Cloud Provider

```bash
# Build and tag
docker build -t yourusername/resilio-app:latest .

# Push to Docker Hub
docker push yourusername/resilio-app:latest

# Deploy on any platform (AWS ECS, Azure Container Instances, etc.)
```

### 🔐 Environment Variables

Required environment variables for full functionality:
- `GOOGLE_API_KEY`: For Gemini LLM (optional if `USE_REAL_LLM=False`)
- `TAVILY_API_KEY`: For live web search verification (optional)

**Note**: The app runs in "Safe Mode" (deterministic mock) if API keys are not provided.

### 🏥 Health Checks

The Dockerfile includes a health check endpoint that container orchestration platforms can use:
- Endpoint: `http://localhost:8080/_stcore/health`
- Interval: 30 seconds
- Timeout: 10 seconds

### 📊 Resource Recommendations

For Google Cloud Run:
- **CPU**: 1-2 vCPU
- **Memory**: 2-4 GB
- **Concurrency**: 10-80 requests per instance
- **Min Instances**: 0 (for cost savings) or 1 (for faster cold starts)

### 🐛 Troubleshooting

1. **Port Issues**: Ensure Cloud Run uses PORT environment variable or set it to 8080
2. **API Keys**: Use Cloud Run secrets manager for sensitive keys
3. **Cold Starts**: Consider setting min instances to 1 for production
4. **Memory**: Increase if you see OOM errors during Monte Carlo simulations

### ✅ Pre-Deployment Checklist

- [x] Dockerfile optimized with layer caching
- [x] `.dockerignore` created to exclude unnecessary files
- [x] Health checks configured
- [x] Port and address settings correct for cloud
- [x] Environment variables documented
- [x] Code syntax errors fixed
- [x] Tests passing locally

### 🎯 Next Steps

1. Set up Google Cloud Project
2. Enable Cloud Run API
3. Configure API keys as secrets
4. Build and deploy using commands above
5. Test the deployed endpoint
6. Set up monitoring and logging

