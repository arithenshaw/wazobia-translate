from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
import logging
import requests
from functools import lru_cache
import re
import html

# -----------------------------------------------------------------------------
# App + CORS + Logging
# -----------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wazobia")

# -----------------------------------------------------------------------------
# Language codes + dictionary
# -----------------------------------------------------------------------------
LANGUAGE_CODES = {
    "english": "en",
    "yoruba": "yo",
    "hausa": "ha",
    "igbo": "ig",
}

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

    # Reverse mappings
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

# -----------------------------------------------------------------------------
# Helpers: language detection + MyMemory + translation
# -----------------------------------------------------------------------------
def detect_language(text: str):
    """Heuristic detection among english/yoruba/hausa/igbo."""
    if not text:
        return "english", 0.6

    text_lower = text.lower().strip()
    if text_lower in TRANSLATION_DICT:
        translations = TRANSLATION_DICT[text_lower]
        if {"yoruba", "hausa", "igbo"} <= set(translations.keys()):
            return "english", 0.95
        if "english" in translations:
            if "yoruba" in translations:
                return "hausa", 0.9
            if "hausa" in translations:
                return "yoruba", 0.9
            return "igbo", 0.9

    yoruba_markers = ["ẹ", "ọ", "ṣ", "gb", "kp"]
    hausa_markers = ["ɗ", "ƙ", "ts", "sh", "ƴ"]
    igbo_markers = ["ị", "ọ", "ụ", "ṅ", "nw"]

    scores = {
        "yoruba": sum(1 for m in yoruba_markers if m in text_lower),
        "hausa": sum(1 for m in hausa_markers if m in text_lower),
        "igbo": sum(1 for m in igbo_markers if m in text_lower),
    }
    if max(scores.values()) > 0:
        lang = max(scores, key=scores.get)
        return lang, 0.7

    return "english", 0.6


@lru_cache(maxsize=1000)
def translate_with_mymemory(text: str, source_lang: str, target_lang: str):
    """Free MyMemory translate (no key)."""
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": text,
            "langpair": f"{LANGUAGE_CODES.get(source_lang,'en')}|{LANGUAGE_CODES.get(target_lang,'en')}"
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("responseStatus") == 200:
                translated = data["responseData"]["translatedText"]
                if translated and translated.lower() != text.lower():
                    return translated
        logger.warning(f"MyMemory failed {source_lang}->{target_lang}")
        return None
    except Exception as e:
        logger.error(f"MyMemory error: {e}")
        return None


def translate_text(text: str, source_lang: str | None = None):
    """
    Hybrid flow:
    1) exact dictionary -> instant
    2) otherwise MyMemory to targets (fan-out)
    """
    text_clean = text.strip()
    text_lower = text_clean.lower()

    if not source_lang:
        source_lang, _ = detect_language(text_clean)

    # dictionary hit
    if text_lower in TRANSLATION_DICT:
        translations = TRANSLATION_DICT[text_lower].copy()
        result = {
            "input": text_clean,
            "detected_language": source_lang,
            "translations": {},
            "source": "dictionary",
            "found": True,
        }
        if source_lang == "english":
            result["translations"] = {
                "yoruba": translations.get("yoruba", "N/A"),
                "hausa": translations.get("hausa", "N/A"),
                "igbo": translations.get("igbo", "N/A"),
            }
        else:
            result["translations"]["english"] = translations.get("english", "N/A")
            for lang in ["yoruba", "hausa", "igbo"]:
                if lang != source_lang and lang in translations:
                    result["translations"][lang] = translations[lang]
        return result

    # API fan-out
    result = {
        "input": text_clean,
        "detected_language": source_lang,
        "translations": {},
        "source": "mymemory",
        "found": False,
    }

    targets = (
        ["yoruba", "hausa", "igbo"]
        if source_lang == "english"
        else ["english"] + [l for l in ["yoruba", "hausa", "igbo"] if l != source_lang]
    )

    success = 0
    for tgt in targets:
        tr = translate_with_mymemory(text_clean, source_lang, tgt)
        if tr:
            result["translations"][tgt] = tr
            success += 1
        else:
            result["translations"][tgt] = "Translation unavailable"

    result["found"] = success > 0
    if not result["found"]:
        result["message"] = (
            "Translation service temporarily unavailable. "
            "Try a common word from the dictionary or try again."
        )
    return result

# -----------------------------------------------------------------------------
# Telex helpers (payload parsing + HTML stripping)
# -----------------------------------------------------------------------------
TAG_RE = re.compile(r"<[^>]+>")
QUOTE_RE = re.compile(r'["“”](.+?)["“”]')

def strip_html(s: str) -> str:
    if not isinstance(s, str):
        return ""
    return TAG_RE.sub("", html.unescape(s)).strip()

def extract_user_text(jsonrpc_payload: dict) -> str:
    """
    Extract text from Telex JSON-RPC payload:
    - message.parts[].text
    - also reads nested 'kind:data' arrays with text items
    - ignores helper lines like "Translating 'hello'..."
    """
    params = (jsonrpc_payload.get("params") or {})
    msg = params.get("message") or {}
    parts = msg.get("parts") or []
    texts = []

    for p in parts:
        if not isinstance(p, dict):
            continue
        if p.get("kind") == "text":
            t = strip_html(p.get("text", ""))
            if t and not t.lower().startswith("translating "):
                texts.append(t)
        elif p.get("kind") == "data":
            for dp in (p.get("data") or []):
                if dp.get("kind") == "text":
                    t = strip_html(dp.get("text", ""))
                    if t and not t.lower().startswith("translating "):
                        texts.append(t)

    return " ".join(texts).strip()

# -----------------------------------------------------------------------------
# Public endpoints
# -----------------------------------------------------------------------------
@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "service": "WazobiaTranslate Agent",
        "version": "2.1",
        "features": {
            "dictionary_words": len(TRANSLATION_DICT),
            "api_translation": "MyMemory (FREE)",
            "sentence_support": True,
        },
        "supported_languages": ["English", "Yoruba", "Hausa", "Igbo"],
        "endpoints": {
            "translate": "/translate",
            "a2a_agent": "/a2a/agent/wazobiaAgent",
            "health": "/health",
            "dictionary": "/dictionary",
        },
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dictionary_size": len(TRANSLATION_DICT)
    })

@app.route("/translate", methods=["POST"])
def translate_http():
    try:
        data = request.get_json() or {}
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"error": "Missing 'text' field"}), 400
        source_lang = data.get("source_language")
        result = translate_text(text, source_lang)
        return jsonify(result)
    except Exception as e:
        logger.error(f"/translate error: {e}", exc_info=True)
        return jsonify({"error": "internal"}), 500

@app.route("/dictionary")
def get_dictionary():
    categories = {
        "greetings": ["hello", "good morning", "good afternoon", "good evening", "good night", "welcome", "how are you"],
        "basic": ["come", "go", "eat", "drink", "water", "food", "house", "road", "market", "money"],
        "courtesy": ["thank you", "please", "yes", "no", "sorry", "excuse me"],
        "family": ["father", "mother", "child", "brother", "sister", "husband", "wife", "family"],
        "numbers": ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"],
        "verbs": ["love", "know", "see", "hear", "speak", "sleep", "work", "read", "write"],
        "time": ["today", "tomorrow", "yesterday"],
    }
    return jsonify({
        "total_words": len(TRANSLATION_DICT),
        "categories": categories,
        "note": "Dictionary words are instant; other vocabulary uses MyMemory free API."
    })

# -----------------------------------------------------------------------------
# Telex A2A endpoint (JSON-RPC 2.0)
# -----------------------------------------------------------------------------
@app.route("/a2a/agent/wazobiaAgent", methods=["POST"])
def a2a_agent():
    try:
        payload = request.get_json() or {}
        logger.info(f"Received A2A request: {payload}")

        params = payload.get("params") or {}
        cfg = params.get("configuration") or {}
        blocking = bool(cfg.get("blocking", False))

        push_cfg = cfg.get("pushNotificationConfig") or {}
        webhook_url = push_cfg.get("url")
        webhook_token = push_cfg.get("token")

        in_message = params.get("message") or {}
        incoming_message_id = in_message.get("messageId") or params.get("messageId")

        # 1) extract user text and normalize
        raw_text = extract_user_text(payload)

        # support `translate "..."` and `translate ...`
        m = QUOTE_RE.search(raw_text)
        if m:
            raw_text = m.group(1)
        raw_text = raw_text.replace("translate ", "").replace("please ", "").strip()

        # 2) compose reply text
        if not raw_text:
            reply_text = (
                "👋 **WazobiaTranslate** here!\n"
                "Send a word or sentence and I’ll translate between **English, Yoruba, Hausa, and Igbo**.\n"
                "Examples: *hello*, *good morning*, *translate \"water\"*"
            )
        else:
            result = translate_text(raw_text)
            if result.get("found"):
                lines = ["🌍 **Translation**", f"📝 *{raw_text}*"]
                if result.get("source") == "dictionary":
                    lines.append("📚 Source: Curated Dictionary")
                else:
                    lines.append("🤖 Source: MyMemory (FREE)")
                lines.append("")
                lines.append("🗣️ **Translations:**")
                for lang, tr in result["translations"].items():
                    if tr and tr != "Translation unavailable":
                        lines.append(f"- **{lang.capitalize()}**: {tr}")
                reply_text = "\n".join(lines)
            else:
                reply_text = (
                    f"❌ Couldn't translate *{raw_text}* right now.\n"
                    f"{result.get('message','Try a common word or add quotes, e.g., translate \"good morning\"')}")

        response_message = {
            "kind": "message",
            "role": "assistant",
            "parts": [{"kind": "text", "text": reply_text}],
        }

        # 3) deliver based on blocking flag
        if not blocking:
            # webhook delivery is required; include messageId
            if webhook_url and webhook_token:
                webhook_body = {
                    "jsonrpc": "2.0",
                    "method": "message/receive",
                    "params": {
                        "message": response_message,
                        "messageId": incoming_message_id,  # critical to attach to the thread
                    },
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {webhook_token}",
                }
                try:
                    wr = requests.post(webhook_url, json=webhook_body, headers=headers, timeout=8)
                    logger.info(f"Webhook POST -> {wr.status_code} {wr.text[:200]}")
                except Exception as e:
                    logger.error(f"Webhook error: {e}", exc_info=True)

            # RPC ack for non-blocking
            if payload.get("jsonrpc") and payload.get("id") is not None:
                return jsonify({"jsonrpc": "2.0", "id": payload["id"], "result": {"status": "queued"}}), 200
            return jsonify({"status": "queued"}), 200

        # blocking=true: return the message directly in the RPC result
        if payload.get("jsonrpc") and payload.get("id") is not None:
            return jsonify({"jsonrpc": "2.0", "id": payload["id"], "result": {"message": response_message}}), 200
        return jsonify({"message": response_message}), 200

    except Exception as e:
        logger.error(f"A2A error: {e}", exc_info=True)
        j = request.get_json(silent=True) or {}
        if j.get("jsonrpc") and j.get("id") is not None:
            return jsonify({
                "jsonrpc": "2.0",
                "id": j["id"],
                "result": {
                    "message": {
                        "kind": "message",
                        "role": "assistant",
                        "parts": [{"kind": "text", "text": "⚠️ An error occurred. Try: hello"}],
                    }
                }
            }), 200
        return jsonify({"error": "internal"}), 200

# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("=" * 60)
    logger.info("🚀 Starting WazobiaTranslate v2.1 (Telex A2A fixes)")
    logger.info(f"📚 Dictionary size: {len(TRANSLATION_DICT)}")
    logger.info("🤖 API: MyMemory (free)")
    logger.info("✅ Blocking & non-blocking delivery supported")
    logger.info("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True)
