from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import PyPDF2
import uuid
from services.company_matcher import CompanyMatcherService

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory session storage (replace with proper database in production)
sessions = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        'resume_text': None,
        'preferences': None,
        'uploaded_file': None
    }
    return session_id

@app.route('/uploadResume', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume file provided'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Extract text from PDF if it's a PDF file
        resume_text = ""
        if filename.lower().endswith('.pdf'):
            try:
                with open(filepath, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        resume_text += page.extract_text()
            except Exception as e:
                return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500
        
        # Create a new session and store resume data
        session_id = create_session()
        sessions[session_id]['resume_text'] = resume_text
        sessions[session_id]['uploaded_file'] = unique_filename
        
        return jsonify({
            'message': 'Resume uploaded successfully',
            'filename': unique_filename,
            'resume_text': resume_text,
            'session_id': session_id
        }), 200
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/submitPreferences', methods=['POST'])
def submit_preferences():
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid or missing session ID'}), 400
    
    required_fields = ['desired_roles', 'industries', 'work_locations', 'company_stages']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
        if not isinstance(data[field], list):
            return jsonify({'error': f'{field} must be an array'}), 400
    
    preferences = {
        'desired_roles': data['desired_roles'],
        'industries': data['industries'],
        'work_locations': data['work_locations'],
        'company_stages': data['company_stages']
    }
    
    # Store preferences in session
    sessions[session_id]['preferences'] = preferences
    
    return jsonify({
        'message': 'Preferences submitted successfully',
        'session_id': session_id,
        'preferences': preferences
    }), 200

@app.route('/getSessionData', methods=['GET'])
def get_session_data():
    session_id = request.args.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid or missing session ID'}), 400
        
    return jsonify({
        'session_data': sessions[session_id]
    }), 200

@app.route('/api/matches', methods=['GET'])
def get_matches():
    session_id = request.args.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid or missing session ID'}), 400
    
    session_data = sessions[session_id]
    
    if not session_data['resume_text']:
        return jsonify({'error': 'No resume found. Please upload a resume first.'}), 400
    
    if not session_data['preferences']:
        return jsonify({'error': 'No preferences found. Please set preferences first.'}), 400

    try:
        matcher = CompanyMatcherService()
        matches = matcher.get_company_matches(
            resume_text=session_data['resume_text'],
            preferences=session_data['preferences']
        )
        
        return jsonify({
            'matches': matches,
            'count': len(matches)
        })
    
    except Exception as e:
        app.logger.error(f"Error getting matches: {str(e)}")
        return jsonify({'error': 'Failed to get company matches'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
