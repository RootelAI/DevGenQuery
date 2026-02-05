from openai import OpenAI
import anthropic
from google import genai


def check_openai(model, api_key):
    try:
        client = OpenAI(api_key=api_key)
        # 간단한 completion 요청으로 테스트
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5
        )
        return True
    except Exception as e:
        return False


def check_anthropic(model, api_key):
    try:
        client = anthropic.Anthropic(api_key=api_key)
        # 간단한 메시지 요청으로 테스트
        client.messages.create(
            model=model,
            max_tokens=5,
            messages=[{"role": "user", "content": "ping"}]
        )
        return True
    except Exception as e:
        return False


def check_gemini(model, api_key):
    try:
        genai.configure(api_key=api_key)
        model_instance = genai.GenerativeModel(model)
        model_instance.generate_content("ping") 
        return True
    except Exception as e:
        return False


def check_api_key(model, api_key):
    key_lower = api_key.lower()
    
    ok = False

    if key_lower.startswith("sk-ant-"):
        ok = check_anthropic(model, api_key)
    elif key_lower.startswith("sk-"):
        ok = check_openai(model, api_key)
    elif key_lower.startswith("aiza"):
        ok = check_gemini(model, api_key)
    else:
        ok = check_gemini(model, api_key)
    
    return ok

