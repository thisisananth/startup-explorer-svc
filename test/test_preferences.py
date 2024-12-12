import requests
import json

def test_submit_preferences(session_id):
    url = 'http://localhost:5001/submitPreferences'
    
    # Sample preferences data
    preferences = {
        'session_id': session_id,
        'desired_roles': ['Software Engineer', 'Technical Lead', 'Engineering Manager'],
        'industries': ['AI/ML', 'Enterprise Software', 'FinTech'],
        'work_locations': ['San Francisco', 'Remote', 'Seattle'],
        'company_stages': ['Seed', 'Series A', 'Series B']
    }
    
    try:
        print("\nSubmitting preferences...")
        response = requests.post(url, json=preferences)
        
        if response.status_code == 200:
            print("\nSuccess! Server response:")
            result = response.json()
            print("\nPreferences submitted:")
            print(json.dumps(result['preferences'], indent=2))
        else:
            print(f"\nError: Server returned status code {response.status_code}")
            print("Response:", response.text)
            
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to the server. Make sure the Flask app is running on port 5001.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")

def test_get_session_data(session_id):
    url = f'http://localhost:5001/getSessionData?session_id={session_id}'
    
    try:
        print("\nFetching session data...")
        response = requests.get(url)
        
        if response.status_code == 200:
            print("\nSuccess! Session data:")
            result = response.json()
            print(json.dumps(result['session_data'], indent=2))
        else:
            print(f"\nError: Server returned status code {response.status_code}")
            print("Response:", response.text)
            
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to the server. Make sure the Flask app is running on port 5001.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")

if __name__ == "__main__":
    # Get session_id from command line or use a test session
    import sys
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not session_id:
        print("Please provide a session_id from the resume upload response")
        sys.exit(1)
        
    test_submit_preferences(session_id)
    test_get_session_data(session_id)
