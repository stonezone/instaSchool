import os
import requests
import sys
from operator import itemgetter

# Try to import SDKs, handle missing gracefully
try:
    import openai
except ImportError:
    openai = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None

# --- Configuration & Base URLs ---
PROVIDERS = {
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "name": "OpenAI",
        "check_func": "check_openai"
    },
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
        "name": "Anthropic",
        "check_func": "check_anthropic"
    },
    "gemini": {
        "env_var": "GOOGLE_API_KEY", 
        "name": "Google Gemini",
        "check_func": "check_google"
    },
    "deepseek": {
        "env_var": "DEEPSEEK_API_KEY",
        "name": "DeepSeek",
        "check_func": "check_deepseek"
    },
    "kimi": {
        "env_var": "MOONSHOT_API_KEY",
        "name": "Kimi.ai (Moonshot)",
        "check_func": "check_kimi"
    }
}

def print_header(text):
    print(f"\n{'-'*60}")
    print(f"Checking {text}...")
    print(f"{'-'*60}")

def format_output(models, provider_name):
    if not models:
        print(f"❌ No models found for {provider_name} (Auth failed or empty list).")
        return

    # Deduplicate and Sort
    unique_models = sorted(list(set(models)))
    
    print(f"✅ Access Confirmed. Found {len(unique_models)} models.")
    
    if tabulate:
        # Create chunks of 3 for cleaner display
        chunk_size = 3
        chunks = [unique_models[i:i + chunk_size] for i in range(0, len(unique_models), chunk_size)]
        print(tabulate(chunks, tablefmt="plain"))
    else:
        for m in unique_models:
            print(f"  - {m}")

def check_openai():
    """Checks OpenAI standard API."""
    api_key = os.getenv(PROVIDERS['openai']['env_var'])
    if not api_key:
        return None
    
    print_header("OpenAI")
    
    if not openai:
        print("❌ 'openai' library not installed. Run: pip install openai")
        return

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.models.list()
        # Filter for standard GPT/DALL-E models to reduce noise (e.g., removing whisper, tts if desired, but keeping all for now)
        return [m.id for m in response.data]
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

def check_anthropic():
    """Checks Anthropic API. Uses requests for robustness as SDK list_models is new."""
    api_key = os.getenv(PROVIDERS['anthropic']['env_var'])
    if not api_key:
        return None
    
    print_header("Anthropic")
    
    try:
        # Direct API call to list models (newer endpoint)
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        response = requests.get("https://api.anthropic.com/v1/models", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return [m['id'] for m in data.get('data', [])]
        else:
            print(f"❌ API Request Failed: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

def check_deepseek():
    """Checks DeepSeek via OpenAI-compatible endpoint."""
    api_key = os.getenv(PROVIDERS['deepseek']['env_var'])
    if not api_key:
        return None
    
    print_header("DeepSeek")
    
    if not openai:
        print("❌ 'openai' library not installed.")
        return

    try:
        client = openai.OpenAI(
            api_key=api_key, 
            base_url="https://api.deepseek.com"
        )
        response = client.models.list()
        return [m.id for m in response.data]
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

def check_kimi():
    """Checks Kimi.ai (Moonshot) via OpenAI-compatible endpoint."""
    api_key = os.getenv(PROVIDERS['kimi']['env_var'])
    if not api_key:
        return None
    
    print_header("Kimi.ai (Moonshot)")
    
    if not openai:
        print("❌ 'openai' library not installed.")
        return

    try:
        client = openai.OpenAI(
            api_key=api_key, 
            base_url="https://api.moonshot.ai/v1"
        )
        response = client.models.list()
        return [m.id for m in response.data]
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

def check_google():
    """Checks Google Gemini."""
    api_key = os.getenv(PROVIDERS['gemini']['env_var'])
    if not api_key:
        # Fallback check for GEMINI_API_KEY just in case
        api_key = os.getenv("GEMINI_API_KEY")
        
    if not api_key:
        return None
        
    print_header("Google Gemini")
    
    if not genai:
        print("❌ 'google-generativeai' library not installed. Run: pip install google-generativeai")
        return

    try:
        genai.configure(api_key=api_key)
        # Iterate over models and filter for 'generateContent' capability
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # Strip the 'models/' prefix for cleaner output
                name = m.name.replace("models/", "")
                models.append(name)
        return models
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

def main():
    print("🔍 Scanning Environment for API Keys...")
    
    keys_found = 0
    
    # Map string function names to actual functions
    func_map = globals()
    
    for key, config in PROVIDERS.items():
        # Check if key exists in env
        if os.getenv(config['env_var']) or (key == 'gemini' and os.getenv("GEMINI_API_KEY")):
            keys_found += 1
            # Call the specific check function
            check_fn = func_map[config['check_func']]
            models = check_fn()
            
            if models is not None:
                format_output(models, config['name'])
        else:
            # Silent skip, or verbose if you prefer
            # print(f"⚪ No key found for {config['name']} ({config['env_var']})")
            pass

    if keys_found == 0:
        print("\n⚠️  No API keys found in environment variables.")
        print("   Make sure you have exported them in your .zshrc or .bashrc")
        print("   Example: export OPENAI_API_KEY='sk-...'")
        print("   Current detected keys: ", [k for k in os.environ.keys() if 'API_KEY' in k])

if __name__ == "__main__":
    main()
