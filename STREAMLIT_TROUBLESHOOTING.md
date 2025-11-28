# Streamlit Troubleshooting Guide

## Issue 1: Ctrl+C Not Stopping Streamlit

### Why This Happens:
- Streamlit sometimes doesn't respond to Ctrl+C if it's running in a background process
- The process might be running in a different terminal session
- Multiple Streamlit instances might be running

### Solutions:

**Option 1: Find and Kill the Process**
```bash
# Find Streamlit processes
ps aux | grep streamlit

# Kill by process ID (replace PID with actual number)
kill -9 <PID>

# Or kill all Streamlit processes
pkill -f streamlit
```

**Option 2: Kill by Port**
```bash
# Find what's using port 8501
lsof -ti:8501

# Kill it
kill -9 $(lsof -ti:8501)
```

**Option 3: Use a Different Port**
```bash
streamlit run ui/dashboard.py --server.port 8502
```

## Issue 2: Blank Page in Browser

### Common Causes:
1. **Wrong Streamlit App Running**: Another app was using port 8501
2. **Import Errors**: Check terminal for error messages
3. **Port Conflict**: Multiple apps trying to use same port

### Solutions:

**Check for Errors:**
```bash
# Run Streamlit in foreground to see errors
streamlit run ui/dashboard.py
```

**Verify the Correct App:**
```bash
# Make sure you're in the right directory
cd "/Users/junchilu/Desktop/2025/AI & Data Science/00_Projects/resilio"

# Activate virtual environment
source venv/bin/activate

# Run the app
streamlit run ui/dashboard.py
```

## Best Practices

### 1. Always Use Virtual Environment
```bash
source venv/bin/activate
streamlit run ui/dashboard.py
```

### 2. Check Port Before Starting
```bash
# Check if port is free
lsof -ti:8501 || echo "Port 8501 is free"

# If not free, kill the process or use different port
```

### 3. Run in Foreground for Debugging
```bash
# Don't use background mode when debugging
streamlit run ui/dashboard.py
# Press Ctrl+C to stop (should work in foreground)
```

### 4. Clean Start Script
```bash
#!/bin/bash
# kill_existing_streamlit.sh

# Kill any existing Streamlit on port 8501
lsof -ti:8501 | xargs kill -9 2>/dev/null

# Wait a moment
sleep 1

# Start fresh
cd "/Users/junchilu/Desktop/2025/AI & Data Science/00_Projects/resilio"
source venv/bin/activate
streamlit run ui/dashboard.py
```

## Current Status

✅ **Fixed Issues:**
- Killed old Streamlit process (PID 5062) that was blocking port 8501
- Started fresh Streamlit instance
- Dashboard should now load correctly at http://localhost:8501

## Quick Commands

**Stop Streamlit:**
```bash
pkill -f "streamlit run ui/dashboard.py"
# or
kill -9 $(lsof -ti:8501)
```

**Start Streamlit:**
```bash
cd "/Users/junchilu/Desktop/2025/AI & Data Science/00_Projects/resilio"
source venv/bin/activate
streamlit run ui/dashboard.py
```

**Check if Running:**
```bash
lsof -ti:8501 && echo "Streamlit is running" || echo "Port is free"
```

