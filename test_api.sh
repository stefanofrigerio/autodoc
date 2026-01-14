#!/bin/bash
PROJECT_ID="it-nonprod-gen-advana-000017"
LOCATION="us-central1"
MODEL="gemini-2.5-flash-lite"

echo "Getting access token..."
ACCESS_TOKEN=$(gcloud auth print-access-token)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Failed to get access token. Run 'gcloud auth login' first."
    exit 1
fi

echo "Calling API..."
curl -v -X POST \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    "https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL}:generateContent" \
    -d '{ "contents": { "role": "USER", "parts": { "text": "Hello" } } }'
