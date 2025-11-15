#!/bin/bash
set -e

echo "=================================================="
echo "  Lizzy 2.0 - Render Build Script"
echo "=================================================="

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p projects
mkdir -p logs

# Download and extract RAG buckets from Google Drive
if [ -n "$RAG_BUCKETS_FILE_ID" ]; then
    echo "📚 Downloading RAG buckets from Google Drive..."
    echo "   File ID: $RAG_BUCKETS_FILE_ID"

    # Use gdown to download large files from Google Drive
    gdown --id "$RAG_BUCKETS_FILE_ID" -O rag_buckets.tar.gz

    if [ -f "rag_buckets.tar.gz" ]; then
        echo "📂 Extracting RAG buckets..."
        tar -xzf rag_buckets.tar.gz

        echo "🧹 Cleaning up tar file..."
        rm rag_buckets.tar.gz

        echo "✅ RAG buckets installed successfully"

        # List what was extracted
        if [ -d "rag_buckets" ]; then
            echo "   Buckets found:"
            ls -lh rag_buckets/
        fi
    else
        echo "❌ Error: Failed to download rag_buckets.tar.gz"
        exit 1
    fi
else
    echo "⚠️  Warning: RAG_BUCKETS_FILE_ID not set. Buckets will not be available."
    echo "   Set RAG_BUCKETS_FILE_ID environment variable to your Google Drive file ID."
    echo "   Example: RAG_BUCKETS_FILE_ID=1aaWh7ZwXgo7ZvC3haH2zMP8pjlCvx5r0"
fi

echo "=================================================="
echo "  Build Complete!"
echo "=================================================="
