from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
import logging
import requests
from functools import lru_cache
from uuid import uuid4

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Language codes for MyMemory API
LANGUAGE_CODES = {
    'english': 'en',
    'yoruba': 'yo',
    'hausa': 'ha',
    'igbo': 'ig'
}

# Full translation dictionary
TRANSLATION_DICT = {
    # Greetings
    "hello": {"yoruba": "bawo", "hausa": "sannu", "igbo": "ndewo"},
    "good morning": {"yoruba": "e kaaro", "hausa": "ina kwana", "igbo": "ututu oma"},
    "good afternoon": {"yoruba": "e kaasan", "hausa": "ina wuni", "igbo": "ehihie oma"},
    "good evening": {"yoruba": "e kaale", "hausa": "ina yini", "igbo": "mgbede oma"},
    "good night": {"yoruba": "o daaro", "hausa": "mu kwana lafiya", "igbo": "ka chi foo"},
    "welcome": {"yoruba": "e kaabo", "hausa": "barka da zuwa", "igbo": "nnọọ"},
    "how are you": {"yoruba": "bawo ni", "hausa": "yaya kake", "igbo": "kedu ka ị mere"},
    
    # Basic words
    "come": {"yoruba": "wa", "hausa": "zo", "igbo": "bia"},
    "go": {"yoruba": "lo", "hausa": "tafi", "igbo": "gaa"},
    "eat": {"yoruba": "je", "hausa": "ci", "igbo": "rie"},
    "drink": {"yoruba": "mu", "hausa": "sha", "igbo": "ṅụọ"},
    "water": {"yoruba": "omi", "hausa": "ruwa", "igbo": "mmiri"},
    "food": {"yoruba": "onje", "hausa": "abinci", "igbo": "nri"},
    "house": {"yoruba": "ile", "hausa": "gida", "igbo": "ụlọ"},
    "road": {"yoruba": "ona", "hausa": "hanya", "igbo": "ụzọ"},
    "market": {"yoruba": "oja", "hausa": "kasuwa", "igbo": "ahịa"},
    "money": {"yoruba": "owo", "hausa": "kudi", "igbo": "ego"},
    
    # Courtesy
    "thank you": {"yoruba": "e seun", "hausa": "na gode", "igbo": "daalụ"},
    "please": {"yoruba": "jowo", "hausa": "don allah", "igbo": "biko"},
    "yes": {"yoruba": "beeni", "hausa": "eh", "igbo": "ee"},
    "no": {"yoruba": "rara", "hausa": "a'a", "igbo": "mba"},
    "sorry": {"yoruba": "ma binu", "hausa": "yi hakuri", "igbo": "ndo"},
    
    # Family
    "father": {"yoruba": "baba", "hausa": "uba", "igbo": "nna"},
    "mother": {"yoruba": "iya", "hausa": "uwa", "igbo": "nne"},
    "child": {"yoruba": "omo", "hausa": "yaro", "igbo": "nwa"},
    
    # Numbers
    "one": {"yoruba": "okan", "hausa": "daya", "igbo": "otu"},
    "two": {"yoruba": "eji", "hausa": "biyu", "igbo": "abụọ"},
    "three": {"yoruba": "eta", "hausa": "uku", "igbo": "atọ"},
    "four": {"yoruba": "erin", "hausa": "hudu", "igbo": "anọ"},
    "five": {"yoruba": "arun", "hausa": "biyar", "igbo": "ise"},
    
    # Verbs
    "love": {"yoruba": "ife", "hausa": "so", "igbo": "hụ n'anya"},
    "know": {"yoruba": "mo", "hausa": "sani", "igbo": "mara"},
    
    # Time
    "today": {"yoruba": "oni", "hausa": "yau", "igbo": "taa"},
    "tomorrow": {"yoruba": "ola", "hausa": "gobe", "igbo": "echi"},
}

def detect_language(text):
    """Detect language of input text"""
    text_lower = text.lower().strip()
    
    if text_lower in TRANSLATION_DICT:
        translations = TRANSLATION_DICT[text_lower]
        if "yoruba" in translations and "hausa" in translations:
            return "english", 0.95
    
    return "english", 0.6

@lru_cache(maxsize=1000)
def translate_with_mymemory(text, source_lang, target_lang):
    """Translate using MyMemory API (FREE)"""
    try:
        url = "https://api.mymemory.translated.net/get"
        
        source_code = LANGUAGE_CODES.get(source_lang, 'en')
        target_code = LANGUAGE_CODES.get(target_lang, 'en')
        
        params = {
            'q': text,
            'langpair': f"{source_code}|{target_code}"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('responseStatus') == 200:
                translation = data['responseData']['translatedText']
                if translation and translation.lower() != text.lower():
                    return translation
        
        return None
            
    except Exception as e:
        logger.error(f"MyMemory error: {str(e)}")
        return None

def translate_text(text, source_lang=None):
    """
    Hybrid translation: Dictionary first, then MyMemory API
    """
    text_clean = text.strip()
    text_lower = text_clean.lower()
    
    if not source_lang:
        source_lang, confidence = detect_language(text_clean)
    
    # Check dictionary first (fast, accurate)
    if text_lower in TRANSLATION_DICT:
        translations = TRANSLATION_DICT[text_lower].copy()
        
        result = {
            "input": text_clean,
            "detected_language": source_lang,
            "translations": {},
            "source": "dictionary",
            "found": True
        }
        
        if source_lang == "english":
            result["translations"] = {
                "yoruba": translations.get("yoruba", "N/A"),
                "hausa": translations.get("hausa", "N/A"),
                "igbo": translations.get("igbo", "N/A")
            }
        
        return result
    
    # Use MyMemory API for unknown words/sentences
    result = {
        "input": text_clean,
        "detected_language": source_lang,
        "translations": {},
        "source": "mymemory",
        "found": False
    }
    
    target_languages = ["yoruba", "hausa", "igbo"] if source_lang == "english" else ["english"]
    
    for target_lang in target_languages:
        translation = translate_with_mymemory(text_clean, source_lang, target_lang)
        
        if translation:
            result["translations"][target_lang] = translation
            result["found"] = True
        else:
            result["translations"][target_lang] = "Translation unavailable"
    
    if not result["found"]:
        result["message"] = "Translation unavailable. Try: hello, water, thank you"
    
    return result

@app.route('/a2a/agent/wazobiaAgent', methods=['POST'])
def a2a_agent():
    """
    A2A Protocol compliant endpoint with MyMemory translation
    Following FastAPI guide structure
    """
    try:
        data = request.get_json()
        logger.info("="*80)
        logger.info("📨 A2A REQUEST")
        
        # Validate JSON-RPC
        if data.get("jsonrpc") != "2.0" or "id" not in data:
            return jsonify({
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "error": {
                    "code": -32600,
                    "message": "Invalid Request"
                }
            }), 400
        
        request_id = data.get("id")
        method = data.get("method")
        
        logger.info(f"🆔 ID: {request_id}")
        logger.info(f"📞 Method: {method}")
        
        # Extract configuration
        config = None
        webhook_url = None
        webhook_token = None
        is_blocking = True
        
        if "params" in data and "configuration" in data["params"]:
            config = data["params"]["configuration"]
            is_blocking = config.get("blocking", True)
            
            if "pushNotificationConfig" in config:
                push_config = config["pushNotificationConfig"]
                webhook_url = push_config.get("url")
                webhook_token = push_config.get("token")
        
        logger.info(f"🔄 Blocking: {is_blocking}")
        
        # Extract messages
        messages = []
        context_id = None
        task_id = None
        
        if method == "message/send":
            if "params" in data and "message" in data["params"]:
                messages = [data["params"]["message"]]
                task_id = data["params"]["message"].get("taskId")
        elif method == "execute":
            if "params" in data:
                messages = data["params"].get("messages", [])
                context_id = data["params"].get("contextId")
                task_id = data["params"].get("taskId")
        
        # Generate IDs
        context_id = context_id or str(uuid4())
        task_id = task_id or str(uuid4())
        
        # Extract user message (take first few clean words)
        user_message = ""
        if messages:
            last_message = messages[-1]
            if "parts" in last_message:
                for part in last_message["parts"]:
                    if part.get("kind") == "text" and part.get("text"):
                        raw_text = part["text"].strip()
                        # Extract first 1-3 words to avoid concatenated history
                        words = raw_text.split()[:3]
                        user_message = " ".join(words)
                        # Remove command words
                        user_message = user_message.replace("translate", "").replace("please", "").strip()
                        break
        
        logger.info(f"✨ Message: '{user_message}'")
        
        # Process translation
        if not user_message or len(user_message) < 2:
            response_text = "WazobiaTranslate\n\nTry: hello, water, good morning, thank you"
            source_info = "welcome"
        else:
            trans_result = translate_text(user_message)
            
            if trans_result.get("found"):
                translations = trans_result["translations"]
                lines = []
                
                for lang, trans in translations.items():
                    if trans and trans != "Translation unavailable":
                        lines.append(f"{lang.capitalize()}: {trans}")
                
                response_text = "\n".join(lines)
                source_info = trans_result.get("source", "unknown")
                
                # Add source indicator
                if source_info == "dictionary":
                    response_text += "\n(instant)"
                elif source_info == "mymemory":
                    response_text += "\n(AI)"
            else:
                response_text = f"'{user_message}' not found\n\nTry: hello, water, good morning, thank you"
                source_info = "error"
        
        logger.info(f"📤 Response ({source_info}): {response_text[:100]}")
        
        # Build A2A compliant response (per FastAPI guide)
        
        # Create response message
        response_message = {
            "kind": "message",
            "role": "assistant",
            "parts": [
                {
                    "kind": "text",
                    "text": response_text
                }
            ],
            "messageId": str(uuid4()),
            "taskId": task_id
        }
        
        # Create task status
        task_status = {
            "state": "completed",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": response_message
        }
        
        # Create task result (CRITICAL: This is what Telex expects!)
        task_result = {
            "id": task_id,
            "contextId": context_id,
            "status": task_status,
            "artifacts": [],
            "history": messages + [response_message],
            "kind": "task"
        }
        
        # If non-blocking, send webhook
        if not is_blocking and webhook_url and webhook_token:
            logger.info("🔔 Sending webhook...")
            
            try:
                webhook_payload = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": task_result
                }
                
                webhook_headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {webhook_token}'
                }
                
                webhook_resp = requests.post(
                    webhook_url,
                    json=webhook_payload,
                    headers=webhook_headers,
                    timeout=10
                )
                
                logger.info(f"✅ Webhook: {webhook_resp.status_code}")
                
                if webhook_resp.status_code == 200:
                    logger.info("🎉 WEBHOOK SUCCESS!")
                else:
                    logger.error(f"Webhook error: {webhook_resp.text[:300]}")
            
            except Exception as e:
                logger.error(f"Webhook exception: {str(e)}")
        
        # Return JSON-RPC response
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": task_result
        }
        
        logger.info("="*80)
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"💥 ERROR: {str(e)}", exc_info=True)
        
        return jsonify({
            "jsonrpc": "2.0",
            "id": data.get("id") if "data" in locals() else None,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": {"details": str(e)}
            }
        }), 500

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agent": "WazobiaTranslate",
        "dictionary_size": len(TRANSLATION_DICT)
    })

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "WazobiaTranslate Agent",
        "version": "2.0 - A2A Compliant",
        "features": {
            "dictionary": f"{len(TRANSLATION_DICT)} words",
            "api": "MyMemory (FREE)",
            "sentence_support": True
        }
    })

@app.route('/dictionary')
def get_dictionary():
    """Return available dictionary words"""
    return jsonify({
        "total_words": len(TRANSLATION_DICT),
        "sample_words": list(TRANSLATION_DICT.keys())[:20]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    logger.info("="*60)
    logger.info("🚀 WazobiaTranslate A2A Agent")
    logger.info("="*60)
    logger.info(f"📚 Dictionary: {len(TRANSLATION_DICT)} words")
    logger.info("🤖 API: MyMemory (FREE)")
    logger.info("💰 Cost: $0 forever")
    logger.info("✅ A2A Protocol: Compliant")
    logger.info("="*60)
    
    app.run(host='0.0.0.0', port=port, debug=True)