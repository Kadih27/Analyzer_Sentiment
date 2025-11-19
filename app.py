import os
import json
from flask import Flask, render_template, request, jsonify
from langdetect import detect, LangDetectException
import langdetect
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import tempfile
from PyPDF2 import PdfReader
from docx import Document

# ==============================
# CONFIGURATION INITIALE
# ==============================

# Fixer la graine pour des résultats reproductibles
langdetect.DetectorFactory.seed = 0

# Charger les variables d'environnement
load_dotenv()

# Initialiser OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("La variable d'environnement OPENAI_API_KEY est manquante.")
client = OpenAI(api_key=OPENAI_API_KEY)

# Chemin de l'historique
HISTORY_FILE = "history.json"

# Créer history.json s'il n'existe pas
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

# ==============================
# FONCTIONS UTILITAIRES
# ==============================

def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history_entry(entry):
    history = load_history()
    history.append(entry)
    if len(history) > 100:
        history = history[-100:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_sentiment_from_openai(text: str):
    prompt = (
        "You are a sentiment analysis system. Analyze the sentiment of the following text. "
        "Respond ONLY with a valid JSON object in this exact format: "
        '{"label": "positive|neutral|negative", "score": 0.0}. '
        "The 'score' must be a confidence value between 0.0 and 1.0. "
        "Do not add any explanation, markdown, or extra text.\n\nText: "
        f"{text}"
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    raw_content = response.choices[0].message.content.strip()
    parsed = json.loads(raw_content)

    label = parsed.get("label")
    score = parsed.get("score")

    if label not in {"positive", "neutral", "negative"}:
        raise ValueError(f"Label invalide : {label}")
    if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
        raise ValueError(f"Score invalide : {score}")

    return {"label": label, "score": float(score)}

# ==============================
# INITIALISATION FLASK
# ==============================

app = Flask(__name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path, extension):
    try:
        if extension == 'txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        elif extension == 'pdf':
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted
            return text
        elif extension == 'docx':
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        else:
            raise ValueError("Format non supporté")
    except Exception as e:
        raise Exception(f"Extraction échouée : {str(e)}")

# ==============================
# ROUTES
# ==============================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify(load_history())

@app.route('/clear-history', methods=['DELETE'])
def clear_history():
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return jsonify({"status": "success", "message": "Historique effacé."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze_sentiment():
    text = None

    # 🔹 Cas 1 : Texte saisi manuellement (JSON)
    if request.content_type == 'application/json':
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'status': 'error', 'message': 'No text provided'}), 400
        text = data['text'].strip()
        if not text:
            return jsonify({'status': 'error', 'message': 'Empty text provided'}), 400

    # 🔹 Cas 2 : Fichier uploadé (multipart/form-data)
    elif request.content_type and request.content_type.startswith('multipart/form-data'):
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'Aucun fichier fourni'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'Fichier vide'}), 400
        if not allowed_file(file.filename):
            return jsonify({'status': 'error', 'message': 'Format non supporté. Utilisez .txt, .pdf ou .docx.'}), 400

        ext = file.filename.rsplit('.', 1)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            file.save(tmp.name)
            try:
                text = extract_text_from_file(tmp.name, ext)
            finally:
                os.unlink(tmp.name)

        if not text or not text.strip():
            return jsonify({'status': 'error', 'message': 'Aucun texte extrait du fichier'}), 400
        text = text.strip()

    else:
        return jsonify({'status': 'error', 'message': 'Type de requête non supporté'}), 415

    # 🔹 Limiter la longueur
    text = text[:5000]

    # 🔹 Détection de langue
    try:
        if len(text) < 3:
            language = 'too-short'
        else:
            sample = text[:min(200, len(text))]
            language = detect(sample)
    except LangDetectException:
        language = 'undetermined'

    # 🔹 Analyse de sentiment
    try:
        sentiment = get_sentiment_from_openai(text)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Analyse échouée : {str(e)}'
        }), 500

    # 🔹 Sauvegarder dans l’historique
    entry = {
        "text": text[:200] + "..." if len(text) > 200 else text,
        "full_text": text,
        "label": sentiment["label"],
        "score": sentiment["score"],
        "language": language,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    save_history_entry(entry)

    return jsonify({
        'status': 'success',
        'label': sentiment['label'],
        'score': sentiment['score'],
        'language': language,
    })

# ==============================
# LANCEMENT
# ==============================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)