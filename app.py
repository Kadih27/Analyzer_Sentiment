import os
import json
from flask import Flask, render_template, request, jsonify
from langdetect import detect, LangDetectException
from langdetect.lang_detect_exception import ErrorCode
import langdetect
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
# Chemin du fichier d'historique
HISTORY_FILE = "history.json"

# Créer le fichier s'il n'existe pas
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history_entry(entry):
    history = load_history()
    history.append(entry)
    # Garder les 100 dernières entrées max
    if len(history) > 100:
        history = history[-100:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# Fixer la graine pour des résultats reproductibles de langdetect
langdetect.DetectorFactory.seed = 0

# Charger les variables d'environnement
load_dotenv()

# Initialiser le client OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("La variable d'environnement OPENAI_API_KEY est manquante.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

def get_sentiment_from_openai(text: str):
    """
    Appelle l'API OpenAI pour analyser le sentiment du texte.
    Retourne un dict avec 'label' (positive|neutral|negative) et 'score' (float entre 0 et 1).
    """
    prompt = (
        "You are a sentiment analysis system. Analyze the sentiment of the following text. "
        "Respond ONLY with a valid JSON object in this exact format: "
        '{"label": "positive|neutral|negative", "score": 0.0}. '
        "The 'score' must be a confidence value between 0.0 and 1.0. "
        "Do not add any explanation, markdown, or extra text.\n\nText: "
        f"{text}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",  # Supporte response_format JSON
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

    except json.JSONDecodeError as e:
        raise Exception(f"OpenAI a renvoyé un JSON invalide : {raw_content}. Erreur : {e}")
    except Exception as e:
        raise Exception(f"Erreur OpenAI : {str(e)}")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/history', methods=['GET'])
def get_history():
    history = load_history()
    return jsonify(history)


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
    # Vérifier le corps de la requête
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400

    text = data['text'].strip()
    if not text:
        return jsonify({'status': 'error', 'message': 'Empty text provided'}), 400

    # Détection de langue
    try:
        if len(text) < 10:
            language = 'short-text'
        else:
            sample = text[:min(200, len(text))]
            language = detect(sample)
    except LangDetectException as e:
        if hasattr(e, 'code') and e.code == ErrorCode.CantDetectLanguage:
            language = 'undetermined'
        else:
            language = 'error'

    # Analyse de sentiment via OpenAI
    try:
        sentiment = get_sentiment_from_openai(text)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Échec de l’analyse de sentiment : {str(e)}'
        }), 500
    

    # Enregistrer dans l’historique
    entry = {
        "text": text[:200] + "..." if len(text) > 200 else text,
        "full_text": text,
        "label": sentiment["label"],
        "score": sentiment["score"],
        "language": language,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    save_history_entry(entry)

    # Réponse réussie
    return jsonify({
        'status': 'success',
        'label': sentiment['label'],
        'score': sentiment['score'],
        'language': language,
        'all_results': [{'label': sentiment['label'], 'score': sentiment['score']}]
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)