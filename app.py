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

# ... (keep your TRANSLATION_DICT and translation functions) ...

# Simplified versions for clarity
TRANSLATION_DICT = {
    "hello": {"yoruba": "bawo", "hausa": "sannu", "igbo": "ndewo"},
    "good morning": {"yoruba": "e kaaro", "hausa": "ina kwana", "igbo": "ututu oma"},
    "water": {"yoruba": "omi", "hausa": "ruwa", "igbo": "mmiri"},
    "thank you": {"yoruba": "e seun", "hausa": "na gode", "igbo": "daalụ"},
}

def detect_language(text):
    text_lower = text.lower().strip()
    if text_lower in TRANSLATION_DICT:
        translations = TRANSLATION_DICT[text_lower]
        if "yoruba" in translations:
            return "english", 0.95
    return "english", 0.6

def translate_text(text):
    text_lower = text.lower().strip()
    
    if text_lower in TRANSLATION_DICT:
        return {
            "input": text,
            "detected_language": "english",
            "translations": TRANSLATION_DICT[text_lower],
            "source": "dictionary",
            "found": True
        }
    
    return {
        "input": text,
        "detected_language": "english",
        "found": False
    }

@app.route('/a2a/agent/wazobiaAgent', methods=['POST'])
def a2a_agent():
    """
    A2A Protocol compliant endpoint - Following FastAPI guide structure
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
                    "message": "Invalid Request: jsonrpc must be '2.0' and id is required"
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
        
        # Generate IDs if not provided
        context_id = context_id or str(uuid4())
        task_id = task_id or str(uuid4())
        
        # Extract user message text
        user_message = ""
        if messages:
            last_message = messages[-1]
            if "parts" in last_message:
                for part in last_message["parts"]:
                    if part.get("kind") == "text" and part.get("text"):
                        # Take first few words to avoid concatenated history
                        words = part["text"].strip().split()[:3]
                        user_message = " ".join(words)
                        user_message = user_message.replace("translate", "").replace("please", "").strip()
                        break
        
        logger.info(f"✨ Message: '{user_message}'")
        
        # Process translation
        if not user_message:
            response_text = "Hello! Try: hello, water, good morning, thank you"
        else:
            result = translate_text(user_message)
            
            if result.get("found"):
                translations = result["translations"]
                lines = []
                for lang, trans in translations.items():
                    lines.append(f"{lang.capitalize()}: {trans}")
                response_text = "\n".join(lines)
            else:
                response_text = f"'{user_message}' not found. Try: hello, water, thank you"
        
        logger.info(f"📤 Response: {response_text}")
        
        # Build A2A compliant response following FastAPI guide
        
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
            "state": "completed",  # or "input-required" for ongoing conversation
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": response_message
        }
        
        # Create task result (this is the key structure!)
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
            logger.info("🔔 Sending webhook (non-blocking mode)...")
            
            try:
                webhook_payload = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": task_result  # Send the full task result!
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
                
                logger.info(f"✅ Webhook status: {webhook_resp.status_code}")
                
                if webhook_resp.status_code == 200:
                    logger.info("🎉 WEBHOOK SUCCESS!")
                else:
                    logger.error(f"Webhook failed: {webhook_resp.text[:500]}")
            
            except Exception as e:
                logger.error(f"Webhook error: {str(e)}")
        
        # Return JSON-RPC response with task result
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": task_result  # Return task result, not just message!
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
    return jsonify({"status": "healthy", "agent": "WazobiaTranslate"})

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "WazobiaTranslate Agent",
        "version": "2.0 - A2A Compliant"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("="*50)
    logger.info("🚀 WazobiaTranslate A2A Agent")
    logger.info("="*50)
    app.run(host='0.0.0.0', port=port, debug=True)