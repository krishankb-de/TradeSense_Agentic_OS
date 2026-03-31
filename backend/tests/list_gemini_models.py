"""
Quick script to list available Gemini models
"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: GOOGLE_API_KEY not set")
    sys.exit(1)

genai.configure(api_key=api_key)

print("Available Gemini models:")
print("=" * 80)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"\nModel: {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Description: {model.description}")
        print(f"  Supported methods: {model.supported_generation_methods}")
