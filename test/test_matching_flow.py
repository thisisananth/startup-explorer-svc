import requests
import os
from pathlib import Path

class MatchingFlowTester:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.session_id = None
        
    def test_upload_resume(self):
        print("\n1. Testing Resume Upload...")
        
        # Get path to a test PDF resume
        test_resume_path = Path(__file__).parent / "test_resume.pdf"
        if not test_resume_path.exists():
            print("Error: test_resume.pdf not found in test directory")
            return False
            
        with open(test_resume_path, 'rb') as f:
            files = {'resume': f}
            response = requests.post(f"{self.base_url}/uploadResume", files=files)
            
        if response.status_code == 200:
            self.session_id = response.json()['session_id']
            print("✓ Resume upload successful")
            print(f"✓ Session ID: {self.session_id}")
            return True
        else:
            print(f"✗ Resume upload failed: {response.json()}")
            return False
            
    def test_submit_preferences(self):
        print("\n2. Testing Preferences Submission...")
        if not self.session_id:
            print("✗ No session ID available")
            return False
            
        preferences = {
            "session_id": self.session_id,
            "desired_roles": ["Software Engineer", "Full Stack Developer"],
            "industries": ["AI/ML", "FinTech"],
            "work_locations": ["San Francisco", "Remote"],
            "company_stages": ["Seed", "Series A"]
        }
        
        response = requests.post(
            f"{self.base_url}/submitPreferences",
            json=preferences
        )
        
        if response.status_code == 200:
            print("✓ Preferences submitted successfully")
            return True
        else:
            print(f"✗ Preferences submission failed: {response.json()}")
            return False
            
    def test_get_matches(self):
        print("\n3. Testing Get Matches...")
        if not self.session_id:
            print("✗ No session ID available")
            return False
            
        response = requests.get(
            f"{self.base_url}/api/matches",
            params={"session_id": self.session_id}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"DEBUG: Raw response: {result}")
            matches = result.get('matches', [])
            print(f"DEBUG: Matches type: {type(matches)}")
           # print(f"DEBUG: Matches content: {matches}")
            
            print(f"✓ Successfully retrieved {result['count']} matches")
            min_score_applied = result.get('min_score_applied', 'N/A')
            print(f"✓ Minimum score applied: {min_score_applied}")  # Using .get() with default value
        
            
            if matches:
                print("\nTop 3 matches:")
                for idx, match in enumerate(matches['matches'][:2]):  # Access first 2 items of the list
                    print(f"\nMatch {idx + 1}:")
                    print(f"Company: {match.get('company_name', 'N/A')}")
                    print(f"Description: {match.get('company_description', 'N/A')}")
                    print(f"Final Score: {match.get('final_score', 0):.2f}")
                    print(f"Vector Similarity: {match.get('similarity_score', 0):.2f}")
                    
                    match_reasons = match.get('match_reasons', {})
                    print("\nMatch Reasons:")
                    print(f"- Industry Match: {match_reasons.get('industry_match', 0):.2f}")
                    print(f"- Technical Match: {match_reasons.get('technical_match', 0):.2f}")
                    print(f"- Experience Match: {match_reasons.get('experience_match', 0):.2f}")
                    print(f"- Growth Match: {match_reasons.get('growth_match', 0):.2f}")
                    print(f"\nReasoning: {match_reasons.get('reasoning', 'N/A')}")
            else:
                print("✗ No matches found above minimum score threshold")
            return True
        else:
            print(f"✗ Getting matches failed: {response.json()}")
            return False
            
    def test_error_cases(self):
        print("\n4. Testing Error Cases...")
        
        # Test invalid session ID
        print("\nTesting invalid session ID...")
        response = requests.get(
            f"{self.base_url}/api/matches",
            params={"session_id": "invalid-session-id"}
        )
        if response.status_code == 400:
            print("✓ Invalid session ID handled correctly")
        else:
            print("✗ Invalid session ID not handled correctly")

def main():
    tester = MatchingFlowTester()
    
    # Run the full flow
    if not tester.test_upload_resume():
        print("Stopping tests due to resume upload failure")
        return
        
    if not tester.test_submit_preferences():
        print("Stopping tests due to preferences submission failure")
        return
        
    tester.test_get_matches()
    tester.test_error_cases()

if __name__ == "__main__":
    main() 