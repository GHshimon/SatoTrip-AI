
import json
import os
from typing import Dict, Any

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "system_settings.json")

DEFAULT_SETTINGS = {
    "gemini_model": "gemini-2.0-flash-exp",
    "temperature": 0.7,
    "grounding": True,
    "system_prompt": """あなたは旅行代理店AIエージェント「SatoTrip」です。
ユーザーの要望に基づいて、最適な旅行プランを作成してください。
出力は必ずJSON形式で行い、以下のスキーマに従ってください..."""
}

def ensure_settings_file():
    if not os.path.exists(os.path.dirname(SETTINGS_FILE)):
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2, ensure_ascii=False)

def get_settings() -> Dict[str, Any]:
    ensure_settings_file()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS

def update_settings(new_settings: Dict[str, Any]) -> Dict[str, Any]:
    ensure_settings_file()
    current_settings = get_settings()
    current_settings.update(new_settings)
    
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current_settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving settings: {e}")
        raise e
        
    return current_settings
