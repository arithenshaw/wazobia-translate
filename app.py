from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
import logging
import requests
from functools import lru_cache

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Language codes for MyMemory API
LANGUAGE_CODES = {
    'english': 'en',
    'yoruba': 'yo',
    'hausa': 'ha',
    'igbo': 'ig'
}

# Curated dictionary for common words (fast, accurate, free)
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
    "excuse me": {"yoruba": "e joo", "hausa": "ka yafe ni", "igbo": "biko gbaghara m"},
    
    # Family
    "father": {"yoruba": "baba", "hausa": "uba", "igbo": "nna"},
    "mother": {"yoruba": "iya", "hausa": "uwa", "igbo": "nne"},
    "child": {"yoruba": "omo", "hausa": "yaro", "igbo": "nwa"},
    "brother": {"yoruba": "arakunrin", "hausa": "dan'uwa", "igbo": "nwanne nwoke"},
    "sister": {"yoruba": "arabinrin", "hausa": "'yar'uwa", "igbo": "nwanne nwanyi"},
    "husband": {"yoruba": "oko", "hausa": "miji", "igbo": "di"},
    "wife": {"yoruba": "iyawo", "hausa": "mata", "igbo": "nwunye"},
    "family": {"yoruba": "ebi", "hausa": "iyali", "igbo": "ezinụlọ"},
    
    # Numbers (1-10)
    "one": {"yoruba": "okan", "hausa": "daya", "igbo": "otu"},
    "two": {"yoruba": "eji", "hausa": "biyu", "igbo": "abụọ"},
    "three": {"yoruba": "eta", "hausa": "uku", "igbo": "atọ"},
    "four": {"yoruba": "erin", "hausa": "hudu", "igbo": "anọ"},
    "five": {"yoruba": "arun", "hausa": "biyar", "igbo": "ise"},
    "six": {"yoruba": "efa", "hausa": "shida", "igbo": "isii"},
    "seven": {"yoruba": "eje", "hausa": "bakwai", "igbo": "asaa"},
    "eight": {"yoruba": "ejo", "hausa": "takwas", "igbo": "asatọ"},
    "nine": {"yoruba": "esan", "hausa": "tara", "igbo": "itoolu"},
    "ten": {"yoruba": "ewa", "hausa": "goma", "igbo": "iri"},
    
    # Common verbs
    "love": {"yoruba": "ife", "hausa": "so", "igbo": "hụ n'anya"},
    "know": {"yoruba": "mo", "hausa": "sani", "igbo": "mara"},
    "see": {"yoruba": "ri", "hausa": "gani", "igbo": "hụ"},
    "hear": {"yoruba": "gbo", "hausa": "ji", "igbo": "nụ"},
    "speak": {"yoruba": "soro", "hausa": "yi magana", "igbo": "kwuo"},
    "sleep": {"yoruba": "sun", "hausa": "kwana", "igbo": "hie ụra"},
    "work": {"yoruba": "ise", "hausa": "aiki", "igbo": "ọrụ"},
    "read": {"yoruba": "ka", "hausa": "karatu", "igbo": "gụọ"},
    "write": {"yoruba": "ko", "hausa": "rubuta", "igbo": "dee"},
    
    # Time
    "today": {"yoruba": "oni", "hausa": "yau", "igbo": "taa"},
    "tomorrow": {"yoruba": "ola", "hausa": "gobe", "igbo": "echi"},
    "yesterday": {"yoruba": "ana", "hausa": "jiya", "igbo": "ụnyaahụ"},
    
    # Reverse mappings (Nigerian languages to English/others)
    "bawo": {"english": "hello", "hausa": "sannu", "igbo": "ndewo"},
    "wa": {"english": "come", "hausa": "zo", "igbo": "bia"},
    "e seun": {"english": "thank you", "hausa": "na gode", "igbo": "daalụ"},
    "sannu": {"english": "hello", "yoruba": "bawo", "igbo": "ndewo"},
    "zo": {"english": "come", "yoruba": "wa", "igbo": "bia"},
    "na gode": {"english": "thank you", "yoruba": "e seun", "igbo": "daalụ"},
    "ndewo": {"english": "hello", "yoruba": "bawo", "hausa": "sannu"},
    "bia": {"english": "come", "yoruba": "wa", "hausa": "zo"},
    "daalụ": {"english": "thank you", "yoruba": "e seun", "hausa": "na gode"},
}

def detect_language(text):
    """Detect the language of the input text using simple heuristics."""
    text_lower = text.lower().strip()
    
    # Check dictionary first
    if text_lower in TRANSLATION_DICT:
        translations = TRANSLATION_DICT[text_lower]
        if "yoruba" in translations and "hausa" in translations and "igbo" in translations:
            return "english", 0.95
        elif "english" in translations:
            # Determine which Nigerian language based on what else is available
            if "yoruba" in translations:
                return "hausa", 0.90
            elif "hausa" in translations:
                return "yoruba", 0.90
            else:
                return "igbo", 0.90
    
    # Character marker-based detection
    yoruba_markers = ["ẹ", "ọ", "ṣ", "gb", "kp"]
    hausa_markers = ["ɗ", "ƙ", "ts", "sh", "ƴ"]
    igbo_markers = ["ị", "ọ", "ụ", "ṅ", "nw"]
    
    yoruba_score = sum(1 for marker in yoruba_markers if marker in text_lower)
    hausa_score = sum(1 for marker in hausa_markers if marker in text_lower)
    igbo_score = sum(1 for marker in igbo_markers if marker in text_lower)
    
    if max(yoruba_score, hausa_score, igbo_score) > 0:
        if yoruba_score > hausa_score and yoruba_score > igbo_score:
            return "yoruba", 0.7
        elif hausa_score > yoruba_score and hausa_score > igbo_score:
            return "hausa", 0.7
        elif igbo_score > yoruba_score and igbo_score > hausa_score:
            return "igbo", 0.7
    
    # Default to English
    return "english", 0.6

@lru_cache(maxsize=1000)
def translate_with_mymemory(text, source_lang, target_lang):
    """
    Translate using MyMemory Translation API (Free, no API key needed).
    Free tier: 1000 words/day
    """
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
                # MyMemory sometimes returns the original if no translation found
                if translation and translation.lower() != text.lower():
                    return translation
        
        logger.warning(f"MyMemory translation failed for {source_lang}->{target_lang}")
        return None
            
    except Exception as e:
        logger.error(f"MyMemory API error: {str(e)}")
        return None

def translate_text(text, source_lang=None):
    """
    Hybrid translation function:
    1. Check dictionary first (instant, 100% accurate)
    2. Fall back to MyMemory API (free, good quality)
    """
    text_clean = text.strip()
    text_lower = text_clean.lower()
    
    # Auto-detect language if not provided
    if not source_lang:
        source_lang, confidence = detect_language(text_clean)
    
    # Step 1: Check dictionary for exact matches
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
        else:
            result["translations"]["english"] = translations.get("english", "N/A")
            for lang in ["yoruba", "hausa", "igbo"]:
                if lang != source_lang and lang in translations:
                    result["translations"][lang] = translations[lang]
        
        return result
    
    # Step 2: Use MyMemory API for sentences and unknown words
    result = {
        "input": text_clean,
        "detected_language": source_lang,
        "translations": {},
        "source": "mymemory",
        "found": False
    }
    
    # Determine target languages
    if source_lang == "english":
        target_languages = ["yoruba", "hausa", "igbo"]
    else:
        target_languages = ["english"] + [lang for lang in ["yoruba", "hausa", "igbo"] if lang != source_lang]
    
    # Translate to each target language
    success_count = 0
    for target_lang in target_languages:
        translation = translate_with_mymemory(text_clean, source_lang, target_lang)
        
        if translation:
            result["translations"][target_lang] = translation
            success_count += 1
        else:
            result["translations"][target_lang] = "Translation unavailable"
    
    # Consider it found if at least one translation succeeded
    if success_count > 0:
        result["found"] = True
    else:
        result["message"] = "Translation service temporarily unavailable. Try a common word from our dictionary or try again in a moment."
    
    return result

@app.route('/')
def home():
    """Service information endpoint."""
    return jsonify({
        "status": "online",
        "service": "WazobiaTranslate Agent",
        "version": "2.0 - MyMemory Edition",
        "features": {
            "dictionary_words": len(TRANSLATION_DICT),
            "api_translation": "MyMemory (FREE)",
            "sentence_support": True,
            "cost": "$0 forever"
        },
        "supported_languages": ["English", "Yoruba", "Hausa", "Igbo"],
        "endpoints": {
            "translate": "/translate",
            "a2a_agent": "/a2a/agent/wazobiaAgent",
            "health": "/health",
            "dictionary": "/dictionary"
        }
    })

@app.route('/health')
def health():
    """Health check for monitoring."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "translation_service": "MyMemory (Free)",
        "dictionary_size": len(TRANSLATION_DICT)
    })

@app.route('/translate', methods=['POST'])
def translate():
    """Translation endpoint."""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({"error": "Missing 'text' field in request"}), 400
        
        text = data['text']
        source_lang = data.get('source_language')
        
        result = translate_text(text, source_lang)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/a2a/agent/wazobiaAgent', methods=['POST'])
def a2a_agent():
    """
    Telex.im A2A protocol endpoint.
    Handles incoming messages from Telex and returns translations.
    """
    try:
        data = request.get_json()
        logger.info(f"Received A2A request: {data}")
        
        # Extract message from different possible formats
        user_message = data.get('message', '') or data.get('text', '') or data.get('input', '')
        
        if not user_message or user_message.strip() == '':
            response_text = (
                "Welcome to WazobiaTranslate!\n\n"
                "I translate between English, Yoruba, Hausa, and Igbo!\n\n"
                "Try me with:\n"
                "- Single words: hello, water, thank you\n"
                "- Phrases: good morning, how are you\n"
                "- Full sentences: I love Nigerian food\n\n"
                "Powered by FREE MyMemory API + curated dictionary"
            )
            
            return jsonify({
                "response": response_text,
                "metadata": {
                    "agent": "WazobiaTranslate",
                    "version": "2.0",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }), 200
        
        logger.info(f"Processing message: {user_message}")
        
        # Process the translation
        result = translate_text(user_message)
        
        logger.info(f"Translation result: {result}")
        
        # Format response for Telex (simpler formatting)
        if result.get('found'):
            translations = result['translations']
            detected = result['detected_language'].capitalize()
            source = result.get('source', 'api')
            
            # Simple, clean response without heavy markdown
            response_text = f"Translation for '{user_message}'\n\n"
            response_text += f"Detected: {detected}\n"
            
            if source == 'dictionary':
                response_text += "Source: Dictionary (instant)\n\n"
            else:
                response_text += "Source: MyMemory AI\n\n"
            
            response_text += "Translations:\n"
            
            for lang, translation in translations.items():
                if translation != "Translation unavailable":
                    response_text += f"- {lang.capitalize()}: {translation}\n"
            
            # Add helpful tip
            if source == 'dictionary':
                response_text += "\nTry a full sentence for AI translation!"
            else:
                response_text += "\nTranslated with AI"
        else:
            response_text = f"Sorry, I couldn't translate '{user_message}'\n\n"
            
            if result.get('message'):
                response_text += f"{result['message']}\n\n"
            
            response_text += "Popular words:\n"
            response_text += "- Greetings: hello, good morning\n"
            response_text += "- Courtesy: thank you, please\n"
            response_text += "- Basic: water, food, house\n\n"
            response_text += "Or try any sentence!"
        
        logger.info(f"Sending response: {response_text[:100]}...")
        
        return jsonify({
            "response": response_text,
            "metadata": {
                "agent": "WazobiaTranslate",
                "version": "2.0",
                "timestamp": datetime.utcnow().isoformat(),
                "found": result.get('found', False),
                "source": result.get('source', 'unknown')
            }
        }), 200
    
    except Exception as e:
        logger.error(f"A2A Agent error: {str(e)}", exc_info=True)
        
        error_response = (
            "An error occurred while translating.\n\n"
            "Please try again or try a different word.\n\n"
            "Tip: Common words work best!"
        )
        
        return jsonify({
            "response": error_response,
            "metadata": {
                "agent": "WazobiaTranslate",
                "error": True,
                "error_message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        }), 200  # Return 200 even on error so Telex can display the message

@app.route('/dictionary')
def get_dictionary():
    """Return available words in the dictionary."""
    categories = {
        "greetings": ["hello", "good morning", "good afternoon", "good evening", "good night", "welcome", "how are you"],
        "basic": ["come", "go", "eat", "drink", "water", "food", "house", "road", "market", "money"],
        "courtesy": ["thank you", "please", "yes", "no", "sorry", "excuse me"],
        "family": ["father", "mother", "child", "brother", "sister", "husband", "wife", "family"],
        "numbers": ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"],
        "verbs": ["love", "know", "see", "hear", "speak", "sleep", "work", "read", "write"],
        "time": ["today", "tomorrow", "yesterday"]
    }
    
    return jsonify({
        "total_words": len(TRANSLATION_DICT),
        "categories": categories,
        "api_support": "MyMemory (unlimited vocabulary via API)",
        "note": "Dictionary words are instant and 100% accurate. Other words use FREE MyMemory API."
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    logger.info("=" * 50)
    logger.info("🚀 Starting WazobiaTranslate v2.0 - MyMemory Edition")
    logger.info("=" * 50)
    logger.info(f"📚 Dictionary: {len(TRANSLATION_DICT)} words")
    logger.info("🤖 API: MyMemory (FREE, no key needed)")
    logger.info("💰 Cost: $0 forever")
    logger.info("✅ Sentence support: Enabled")
    logger.info("⚡ Ready to translate!")
    logger.info("=" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=True)