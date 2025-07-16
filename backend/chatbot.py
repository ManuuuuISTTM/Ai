import os
from openai import OpenAI
from dotenv import load_dotenv

# For web backend
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import uuid

load_dotenv()

api_key = os.getenv("SHAPESINC_API_KEY")
model_name = os.getenv("SHAPESINC_SHAPE_USERNAME")

shapes_client = OpenAI(
    api_key=api_key,
    base_url="https://api.shapes.inc/v1/",
)

# Flask app for web
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def is_image_generation_request(message):
    keywords = ["image", "picture", "draw", "generate", "show me", "create an image", "photo"]
    return any(kw in message.lower() for kw in keywords)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/chat', methods=['POST'])
def chat():
    print('Bot is ready and responding to website messages.')
    data = request.get_json()
    user_message = data.get('message', '')
    image_url = data.get('image_url', None)
    if not user_message and not image_url:
        return jsonify({'error': 'No message or image provided'}), 400
    try:
        # Auto-trigger image generation
        if is_image_generation_request(user_message) and not user_message.strip().startswith("!imagine"):
            user_message = f"!imagine {user_message}"
        if image_url:
            # Multimodal request: text + image
            content = []
            if user_message:
                content.append({"type": "text", "text": user_message})
            content.append({"type": "image_url", "image_url": {"url": image_url}})
            response = shapes_client.chat.completions.create(
                model=f"shapesinc/{model_name}",
                messages=[{"role": "user", "content": content}]
            )
        else:
            # Text only
            response = shapes_client.chat.completions.create(
                model=f"shapesinc/{model_name}",
                messages=[{"role": "user", "content": user_message}]
            )
        reply = response.choices[0].message.content
        # If the reply contains both a description and an image URL, combine them
        # (Assume the API returns markdown or a URL in the reply)
        # If reply is a list, join with newlines
        if isinstance(reply, list):
            reply = '\n\n'.join(str(r) for r in reply)
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate-image', methods=['POST'])
def generate_image():
    data = request.get_json()
    prompt = data.get('prompt', '')
    # TODO: Integrate with a real image generation API (e.g., DALL·E, Stable Diffusion)
    # For now, return a working placeholder image
    image_url = 'https://picsum.photos/400/400'  # Working placeholder image
    return jsonify({'image_url': image_url})

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    # Only allow image files
    if not file.filename or not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
        return jsonify({'error': 'Invalid file type'}), 400
    # Save file with a unique name
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'png'
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    # Return the URL to access the uploaded image
    image_url = f"/uploads/{filename}"
    return jsonify({'image_url': image_url})

@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# CLI chat mode
def cli_chat():
    print(f"Chatting with shapesinc/{model_name}. Type 'exit' to quit.")
    while True:
        user_message = input("You: ")
        if user_message.lower() in ("exit", "quit"): break
        try:
            response = shapes_client.chat.completions.create(
                model=f"shapesinc/{model_name}",
                messages=[{"role": "user", "content": user_message}]
            )
            reply = response.choices[0].message.content
            print(f"Bot: {reply}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'cli':
        cli_chat()
    else:
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=True) 