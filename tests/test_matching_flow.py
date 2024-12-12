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
        print(f"DEBUG: Matches content: {matches}")
        print(f"✓ Successfully retrieved {result['count']} matches")
        print(f"✓ Minimum score applied: {result.get('min_score_applied', 'N/A')}")  # Using .get() with default value
        
        
        if matches:
            print("\nTop 3 matches:")
            for idx, match in enumerate(matches[:3]):  # Access first 3 items of the list
                print(f"\nMatch {idx + 1}:")
                print(f"Company: {match.get('company_name', 'N/A')}")
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