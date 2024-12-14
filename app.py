from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import PyPDF2
import uuid
from services import CompanyMatcherService, OutreachService
from dotenv import load_dotenv
import traceback
from flask_cors import CORS
import logging
import json

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS
cors = CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",  # Keep local development
            "https://resume-matcher-lilac.vercel.app"  # Add Vercel domain
        ],
        "methods": ["POST", "GET", "OPTIONS"],
        "allow_headers": ["Content-Type", "Accept"]
    }
})

@app.before_request
def log_request_info():
    logger.debug('Headers: %s', dict(request.headers))
    logger.debug('Body: %s', request.get_data())
    logger.debug('Args: %s', dict(request.args))
    if request.is_json:
        logger.debug('JSON: %s', request.get_json())

@app.after_request
def after_request(response):
    logger.debug('Response Status: %s', response.status)
    logger.debug('Response Headers: %s', dict(response.headers))
    logger.debug('Response Body: %s', response.get_data())
    
    origin = request.headers.get('Origin')
    if origin in ["http://localhost:3000", "https://resume-matcher-lilac.vercel.app"]:
        response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.errorhandler(400)
def handle_bad_request(e):
    logger.error('Bad Request: %s', str(e))
    logger.error('Request data: %s', request.get_data())
    return jsonify({
        'error': 'Bad Request',
        'message': str(e),
        'request_data': {
            'headers': dict(request.headers),
            'body': request.get_data().decode('utf-8'),
            'args': dict(request.args)
        }
    }), 400

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error('Unhandled Exception: %s', str(e))
    logger.error('Traceback: %s', traceback.format_exc())
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(e),
        'traceback': traceback.format_exc()
    }), 500

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory session storage (replace with proper database in production)
sessions = {}

# Initialize services
matcher_service = CompanyMatcherService()
outreach_service = OutreachService()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        'resume_text': None,
        'preferences': None,
        'uploaded_file': None,
        'matches': None,
        'outreach_packages': None
    }
    return session_id

@app.route('/uploadResume', methods=['POST'])
def upload_resume():
    try:
        logger.info('Processing resume upload')
        if 'resume' not in request.files:
            logger.error('No resume file in request')
            return jsonify({'error': 'No resume file uploaded'}), 400
            
        file = request.files['resume']
        logger.debug('Received file: %s', file.filename)
        
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
    
    except Exception as e:
        logger.error('Error in upload_resume: %s', str(e))
        logger.error('Traceback: %s', traceback.format_exc())
        raise

@app.route('/submitPreferences', methods=['POST'])
def submit_preferences():
    try:
        logger.info('Processing preferences submission')
        data = request.json
        logger.debug('Received preferences data: %s', json.dumps(data, indent=2))
        
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
    
    except Exception as e:
        logger.error('Error in submit_preferences: %s', str(e))
        logger.error('Traceback: %s', traceback.format_exc())
        raise

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
    try:
        logger.info('Processing get matches request')
        session_id = request.args.get('session_id')
        logger.debug('Session ID: %s', session_id)
        
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
            sessions[session_id]['matches'] = matches
            return jsonify({
                'matches': matches,
                'count': len(matches)
            })
        
        except Exception as e:
            app.logger.error(f"Error getting matches: {str(e)}")
            return jsonify({'error': 'Failed to get company matches'}), 500
    
    except Exception as e:
        logger.error('Error in get_matches: %s', str(e))
        logger.error('Traceback: %s', traceback.format_exc())
        raise

@app.route('/api/outreach', methods=['POST'])
def generate_outreach_package():
    """
    Generate outreach package (contacts and cover letter) for a selected company
    """
    try:
        logger.info('Processing outreach package generation')
        data = request.json
        logger.debug('Received data: %s', json.dumps(data, indent=2))
        
        session_id = data.get('session_id')
        company_name = data.get('company_name')
        print(f"DEBUG: Session ID: {session_id}")
        print(f"DEBUG: Company Name: {company_name}")
        if not session_id or not company_name:
            return jsonify({
                'error': 'Missing required parameters: session_id and company_name'
            }), 400
            
        # Get session data
        session_data = sessions[session_id]
       
        if not session_data:
            return jsonify({'error': 'Invalid session ID'}), 400
            
        resume_text = session_data.get('resume_text')
        preferences = session_data.get('preferences', {})
        # Initialize outreach_packages if it doesn't exist
        if 'outreach_packages' not in session_data or session_data['outreach_packages'] is None:
            session_data['outreach_packages'] = {}
         
        # Get company info from previous matches
        matches = session_data.get('matches', {})
        matches = matches.get('matches', [])
        
        company_info = None
        for match in matches:
            if match.get('company_name') == company_name:
                company_info = {
                    'company_name': match.get('company_name'),
                    'company_description': match.get('company_description'),
                    'industry': match.get('metadata', {}).get('industry'),
                }
                break
                
        if not company_info:
            return jsonify({'error': 'Company not found in matches'}), 404
            
        # Generate outreach package
        outreach_package = outreach_service.get_outreach_package(
            resume_text=resume_text,
            company_info=company_info,
            role_preference=preferences.get('desired_roles', [''])[0]
        )
        print(f"DEBUG: Outreach Package: {outreach_package}")
        # Store the outreach package in session data (optional)
        session_data['outreach_packages'] = session_data.get('outreach_packages', {})
        session_data['outreach_packages'][company_name] = outreach_package
        
        return jsonify({
            'success': True,
            'outreach_package': {
                'company_name': company_info['company_name'],
                'contacts': outreach_package['contacts'],
                'cover_letter': outreach_package['cover_letter']
            }
        })
        
    except Exception as e:
        logger.error('Error in generate_outreach_package: %s', str(e))
        logger.error('Traceback: %s', traceback.format_exc())
        raise

@app.route('/')
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Startup Explorer Service is running'
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
