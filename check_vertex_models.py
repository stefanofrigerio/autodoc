import vertexai
from vertexai.preview.generative_models import GenerativeModel
import os

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

if not project_id:
    # Try to get from gcloud if not env
    import subprocess
    try:
        project_id = subprocess.check_output(["gcloud", "config", "get-value", "project"]).decode().strip()
    except:
        print("Could not determine project ID")
        exit(1)

print(f"Project: {project_id}, Location: {location}")

regions = ["us-central1", "us-east4", "europe-west1", "europe-west4"]
models_to_test = ["gemini-1.5-flash-001", "gemini-1.0-pro", "gemini-pro", "gemini-2.5-flash-lite"]

for loc in regions:
    print(f"Testing region: {loc}...")
    vertexai.init(project=project_id, location=loc)
    
    for model_name in models_to_test:
        print(f"  Testing model: {model_name}...")
        try:
            if "gemini" in model_name:
                model = GenerativeModel(model_name)
                response = model.generate_content("Hello")
            else:
                from vertexai.language_models import TextGenerationModel
                model = TextGenerationModel.from_pretrained(model_name)
                response = model.predict("Hello")
                
            print(f"SUCCESS: Found working model {model_name} in region {loc}")
            # If we found the one we want (Gemini), we can verify that specially
            if "gemini" in model_name:
                 print("  Gemini is working!")
        except Exception as e:
            print(f"  Failed {model_name} in {loc}: {e}")
