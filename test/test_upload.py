import requests
import os
import json

def test_upload_resume():
    # API endpoint
    url = 'http://localhost:5001/uploadResume'
    
    # Get the test directory path and construct the PDF path
    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_pdf_path = os.path.join(test_dir, 'test_resume.pdf')
    
    if not os.path.exists(test_pdf_path):
        print(f"Error: Test PDF not found at {test_pdf_path}")
        return
    
    try:
        # Open the PDF file
        with open(test_pdf_path, 'rb') as f:
            # Create the files dictionary for the request
            files = {
                'resume': (os.path.basename(test_pdf_path), f, 'application/pdf')
            }
            
            print(f"Uploading file: {test_pdf_path}")
            # Send POST request
            response = requests.post(url, files=files)
            
            # Check if request was successful
            if response.status_code == 200:
                print("\nSuccess! Server response:")
                result = response.json()
                print("\nSession ID:", result.get('session_id'))
                print("Uploaded file:", result.get('filename'))
                print("Message:", result.get('message'))
                print("\nExtracted text preview (first 200 chars):")
                print(result.get('resume_text')[:200] + "...")
                
                # Return session_id for use in other tests
                return result.get('session_id')
            else:
                print(f"\nError: Server returned status code {response.status_code}")
                print("Response:", response.text)
                
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to the server. Make sure the Flask app is running on port 5001.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
    
    return None

if __name__ == "__main__":
    session_id = test_upload_resume()
    if session_id:
        print("\n=== Use this session_id for testing preferences ===")
        print(f"python3 test_preferences.py {session_id}")
