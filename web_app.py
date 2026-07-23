import os
import logging
from flask import Flask, render_template, request, url_for, send_file, abort
from utils.data_loader import load_and_prepare_dataset
from core.matcher import match_template

app = Flask(__name__, template_folder='web_templates', static_folder='web_static')
app.logger.setLevel(logging.INFO)

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
DATASET_PATH = os.path.join(ROOT_DIR, 'data', 'labels.csv')

def find_images_folder():
    candidates = [
        os.path.join(ROOT_DIR, 'images'),
        os.path.join(ROOT_DIR, '..', 'images', 'images'),
        os.path.join(ROOT_DIR, '..', 'images'),
        os.path.join(ROOT_DIR, '..', '..', 'images', 'images'),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return os.path.abspath(path)
    return os.path.abspath(os.path.join(ROOT_DIR, 'images'))

IMAGES_FOLDER = find_images_folder()
if not os.path.isdir(IMAGES_FOLDER):
    app.logger.warning('Images folder not found at %s', IMAGES_FOLDER)

_df = None
_models = None


def load_models():
    global _df, _models
    if _df is None or _models is None:
        _df, _models = load_and_prepare_dataset(DATASET_PATH)
        app.logger.info('Loaded dataset with %d templates', len(_df))


@app.route('/', methods=['GET'])
def index():
    load_models()
    return render_template('index.html', result=None, error=None, query='')


@app.route('/generate', methods=['POST'])
def generate():
    load_models()
    query = request.form.get('query', '').strip()
    if not query:
        return render_template('index.html', result=None, error='Please enter a phrase to generate a meme.', query=query)

    try:
        best_match, info = match_template(query, _df, _models)
        image_name = best_match['image_name']
        image_url = url_for('image_file', filename=image_name)

        top_results = []
        for _, row in info['top_templates'].head(5).iterrows():
            top_results.append({
                'image_name': row.get('image_name', ''),
                'text': row.get('combined_text', row.get('text_corrected', '')),
                'score': float(info['top_scores'][len(top_results)]) if len(info['top_scores']) > len(top_results) else 0.0,
                'image_url': url_for('image_file', filename=row.get('image_name', ''))
            })

        result = {
            'query': query,
            'image_name': image_name,
            'image_url': image_url,
            'combined_score': float(info.get('combined_score', 0.0)),
            'tfidf_score': float(info.get('tfidf_score', 0.0)),
            'semantic_score': float(info.get('semantic_score', 0.0)),
            'sentiment_score': float(info.get('sentiment_score', 0.0)),
            'top_results': top_results,
        }
        return render_template('index.html', result=result, error=None, query=query)
    except Exception as exc:
        app.logger.exception('Error generating meme')
        return render_template('index.html', result=None, error=f'Generation failed: {exc}', query=query)


from flask import redirect

@app.route('/image/<path:filename>')
def image_file(filename):
    safe_path = os.path.normpath(os.path.join(IMAGES_FOLDER, filename))
    if not safe_path.startswith(IMAGES_FOLDER) or not os.path.isfile(safe_path):
        return redirect(f"https://placehold.co/600x400?text={filename}")
    return send_file(safe_path)


if __name__ == '__main__':
    load_models()
    app.run(host='0.0.0.0', port=5000, debug=True)
