
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, AudioConfig, ResultReason, SpeechSynthesisCancellationDetails, CancellationReason
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
import json
import uuid
import os
import configparser
from werkzeug.utils import secure_filename
import google.generativeai as genai

# Load API keys from config.ini
config = configparser.ConfigParser()
config.read('config.ini')
subscription_key = config.get('API_KEYS', 'azure_subscription_key')
region = config.get('API_KEYS', 'azure_region')
speech_endpoint = config.get('API_KEYS', 'azure_speech_endpoint', fallback=None)  
gemini_api_key = config.get('API_KEYS', 'gemini_api_key')
azure_computer_vision_key = config.get('API_KEYS', 'azure_computer_vision_key')
azure_computer_vision_endpoint = config.get('API_KEYS', 'azure_computer_vision_endpoint')

# Print the endpoint 
print(f"Azure Computer Vision Endpoint: {azure_computer_vision_endpoint}")
if speech_endpoint:
    print(f"Azure Speech Endpoint: {speech_endpoint}")  



    genai.configure(api_key=gemini_api_key)

# Initialize Azure Computer Vision client
computervision_client = ComputerVisionClient(azure_computer_vision_endpoint, CognitiveServicesCredentials(azure_computer_vision_key))

app = Flask(__name__)
CORS(app)

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'docx', 'txt', 'zip'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# JSON file paths
USER_CONTEXT_FILE = "user_context.json"
GEMINI_CONTEXT_FILE = "gemini_context.json"

# Load user context from a JSON file
def load_user_context():
    try:
        with open(USER_CONTEXT_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save user context to a JSON file
def save_user_context(context):
    with open(USER_CONTEXT_FILE, "w") as f:
        json.dump(context, f, indent=4)

# Load Gemini context from a JSON file
def load_gemini_context():
    try:
        with open(GEMINI_CONTEXT_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save Gemini context to a JSON file
def save_gemini_context(context):
    with open(GEMINI_CONTEXT_FILE, "w") as f:
        json.dump(context, f, indent=4)

# Speech synthesis function
def synthesize_speech(text, voice_name="zu-ZA-ThandoNeural", pitch="0%", rate="1.0"):
    output_filename = str(uuid.uuid4()) + ".wav"
    output_path = os.path.join(UPLOAD_FOLDER, output_filename)
    
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Configure audio output
    audio_config = AudioConfig(filename=output_path)
    
    # Configure speech synthesis
    if speech_endpoint:
        # Use the explicit endpoint if provided
        speech_config = SpeechConfig(endpoint=speech_endpoint, subscription=subscription_key)
    else:
        # Fallback to using region if endpoint is not provided
        speech_config = SpeechConfig(subscription=subscription_key, region=region)
    
    synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    # Create SSML with the provided text and voice settings
    ssml_text = f"""
    <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{voice_name[:5]}'>
        <voice name='{voice_name}'>
            <prosody pitch='{pitch}' rate='{rate}'>
                {text}
            </prosody>
        </voice>
    </speak>
    """

    try:
        # Synthesize speech
        result = synthesizer.speak_ssml_async(ssml_text).get()

        if result.reason == ResultReason.SynthesizingAudioCompleted:
            print(f"Speech synthesis succeeded. Audio saved to {output_filename}")
            return output_filename
        elif result.reason == ResultReason.Canceled:
            cancellation_details = SpeechSynthesisCancellationDetails(result)
            print("Speech synthesis canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))
                raise Exception(cancellation_details.error_details)
            raise Exception(cancellation_details.reason)
        else:
            raise Exception(f"Speech synthesis failed with reason: {result.reason}")
    except Exception as e:
        print(f"Error during speech synthesis: {e}")
        raise Exception(f"Speech synthesis failed: {str(e)}")

# Azure OCR function to extract text from images and PDFs
def extract_text_from_file(file):
    if file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        # For images
        recognize_results = computervision_client.read_in_stream(file, raw=True)
    elif file.filename.lower().endswith('.pdf'):
        # For PDFs
        recognize_results = computervision_client.read_in_stream(file, raw=True)
    else:
        return None

    if recognize_results is None:
        raise Exception("Failed to get a response from the Computer Vision API")

    operation_location = recognize_results.headers.get("Operation-Location")
    if operation_location is None:
        raise Exception("Operation-Location header not found in the response")

    operation_id = operation_location.split("/")[-1]

    while True:
        result = computervision_client.get_read_result(operation_id)
        if result.status.lower() not in ['notstarted', 'running']:
            break

    if result.status == OperationStatusCodes.succeeded:
        text = ""
        for page in result.analyze_result.read_results:
            for line in page.lines:
                text += line.text + "\n"
        return text
    return None

# New feature: Image Analysis
def analyze_image(file):
    analyze_results = computervision_client.analyze_image_in_stream(file, visual_features=["Categories", "Description", "Color", "Tags", "Faces", "Objects"])
    if analyze_results is None:
        raise Exception("Failed to get a response from the Computer Vision API")

    return analyze_results.as_dict()

# New feature: Image Moderation
def moderate_image(file):
    moderation_results = computervision_client.analyze_image_in_stream(file, visual_features=["Adult"])
    if moderation_results is None:
        raise Exception("Failed to get a response from the Computer Vision API")

    return moderation_results.as_dict()

# New feature: Face Detection
def detect_faces(file):
    face_results = computervision_client.analyze_image_in_stream(file, visual_features=["Faces"])
    if face_results is None:
        raise Exception("Failed to get a response from the Computer Vision API")

    return face_results.as_dict()

# Root route to serve the HTML file
@app.route('/')
def index():
    return render_template('index.html')  

# Route to serve audio files
@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Endpoint to set hackathon goals
@app.route('/set_hackathon_goals', methods=['POST'])
def set_hackathon_goals():
    data = request.json
    if "goals" not in data:
        return jsonify({"error": "Hackathon goals are required"}), 400

    save_gemini_context({"hackathon_goals": data["goals"]})
    return jsonify({"message": "Hackathon goals saved successfully"}), 200

# Endpoint to analyze files with Azure Computer Vision
@app.route('/analyze_with_azure', methods=['POST'])
def analyze_with_azure():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and any(file.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        try:
            # Extract text from the file
            extracted_text = extract_text_from_file(file)
            if not extracted_text:
                return jsonify({"error": "No text could be extracted from the file"}), 400

            return jsonify({
                "status": "Analysis complete",
                "extracted_text": extracted_text
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "File type not allowed"}), 400

# # Endpoint to analyze extracted text with Gemini
# @app.route('/analyze_with_gemini', methods=['POST'])
# def analyze_with_gemini():
#     data = request.json
#     if "extracted_text" not in data:
#         return jsonify({"error": "Extracted text is required"}), 400

#     hackathon_goals = load_gemini_context().get("hackathon_goals", "")
#     if not hackathon_goals:
#         return jsonify({"error": "Hackathon goals are not set"}), 400

#     try:
#         # Generate feedback using Gemini
#         model = genai.GenerativeModel('gemini-2.0-flash')
#         response = model.generate_content(
#             f"Hackathon Goals: {hackathon_goals}\n\nExtracted Text: {data['extracted_text']}\n\nAnalyze this project submission and provide feedback."
#         )
#         feedback = response.text

#         return jsonify({
#             "status": "Analysis complete",
#             "feedback": feedback
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# Modify the analyze_with_gemini endpoint to save extracted text in context
@app.route('/analyze_with_gemini', methods=['POST'])
def analyze_with_gemini():
    data = request.json
    if "extracted_text" not in data:
        return jsonify({"error": "Extracted text is required"}), 400

    hackathon_goals = load_gemini_context().get("hackathon_goals", "")
    if not hackathon_goals:
        return jsonify({"error": "Hackathon goals are not set"}), 400

    try:
        # Generate feedback using Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            f"Hackathon Goals: {hackathon_goals}\n\nExtracted Text: {data['extracted_text']}\n\nAnalyze this project submission and provide feedback."
        )
        feedback = response.text

        # Save the extracted text in the context for future chat reference
        context = load_gemini_context()
        context["extracted_text"] = data['extracted_text']
        save_gemini_context(context)

        return jsonify({
            "status": "Analysis complete",
            "feedback": feedback
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# OCR Endpoint to extract text from images
@app.route('/extract_text', methods=['POST'])
def extract_text():
    if 'image' not in request.files:
        return jsonify({'status': 'Image file not found'}), 400

    image = request.files['image']
    try:
        extracted_text = extract_text_from_file(image)
        return jsonify({'status': 'Text extraction complete', 'extracted_text': extracted_text})
    except Exception as e:
        print(f"Error during text extraction: {e}")
        return jsonify({'status': 'Text extraction failed', 'error': str(e)}), 500

# New endpoint to analyze images
@app.route('/analyze_image', methods=['POST'])
def analyze_image_route():
    if 'image' not in request.files:
        return jsonify({'status': 'Image file not found'}), 400

    image = request.files['image']
    try:
        analysis_results = analyze_image(image)
        return jsonify({'status': 'Image analysis complete', 'results': analysis_results})
    except Exception as e:
        print(f"Error during image analysis: {e}")
        return jsonify({'status': 'Image analysis failed', 'error': str(e)}), 500

# New endpoint to moderate images
@app.route('/moderate_image', methods=['POST'])
def moderate_image_route():
    if 'image' not in request.files:
        return jsonify({'status': 'Image file not found'}), 400

    image = request.files['image']
    try:
        moderation_results = moderate_image(image)
        return jsonify({'status': 'Image moderation complete', 'results': moderation_results})
    except Exception as e:
        print(f"Error during image moderation: {e}")
        return jsonify({'status': 'Image moderation failed', 'error': str(e)}), 500

# New endpoint to detect faces
@app.route('/detect_faces', methods=['POST'])
def detect_faces_route():
    if 'image' not in request.files:
        return jsonify({'status': 'Image file not found'}), 400

    image = request.files['image']
    try:
        face_results = detect_faces(image)
        return jsonify({'status': 'Face detection complete', 'results': face_results})
    except Exception as e:
        print(f"Error during face detection: {e}")
        return jsonify({'status': 'Face detection failed', 'error': str(e)}), 500

# Chat with Gemini and synthesize response
    
# @app.route('/chat', methods=['POST'])
# def chat():
#     data = request.json
#     message = data['message']
#     try:
#         model = genai.GenerativeModel('gemini-2.0-flash')
#         response = model.generate_content(message)
#         return jsonify({'response': response.text})
#     except Exception as e:
#         print(f"Error during chat with Gemini: {e}")
#         return jsonify({'status': 'Chat failed', 'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data['message']
    
    # Load the context from previous project analysis
    context = load_gemini_context()
    
    # Check if there's a project context available
    hackathon_goals = context.get("hackathon_goals", "")
    extracted_text = context.get("extracted_text", "")
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # If project context exists, incorporate it into the chat
        if hackathon_goals or extracted_text:
            full_context = f"""
            Project Context:
            Hackathon Goals: {hackathon_goals}
            Project Submission Details: {extracted_text}

            User Query: {message}
            
            Please provide a response that takes into account the project context.
            """
            response = model.generate_content(full_context)
        else:
            # If no project context, proceed with a standard chat
            response = model.generate_content(message)
        
        return jsonify({'response': response.text})
    except Exception as e:
        print(f"Error during chat with Gemini: {e}")
        return jsonify({'status': 'Chat failed', 'error': str(e)}), 500

# Endpoint to synthesize Gemini response
@app.route('/synthesize_response', methods=['POST'])
def synthesize_response():
    data = request.json
    text = data.get('text')
    voice_name = data.get('voice_name', "zu-ZA-ThandoNeural")
    pitch = data.get('pitch', "0%")
    rate = data.get('rate', "1.0")

    if not text:
        return jsonify({'status': 'Speech synthesis failed', 'error': 'No text provided'}), 400

    try:
        audio_file = synthesize_speech(text, voice_name, pitch, rate)
        return jsonify({'status': 'Speech synthesis complete', 'audio_file': audio_file})
    except Exception as e:
        print(f"Error during speech synthesis: {e}")
        return jsonify({'status': 'Speech synthesis failed', 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)