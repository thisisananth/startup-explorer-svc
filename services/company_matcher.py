from openai import OpenAI
import chromadb
from typing import List, Dict
import json
from dotenv import load_dotenv
import os
load_dotenv()

class CompanyMatcherService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.chroma_client = chromadb.PersistentClient(
            path=os.getenv("CHROMA_DB_PATH", "./data/chromadb")
        )
        self.collection = self.chroma_client.get_collection("startup_press_releases")

    def _create_embedding(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding

    def _prepare_search_text(self, resume_text: str, preferences: Dict) -> str:
        # Combine resume and preferences into a single search query
        search_text = f"""
        Resume: {resume_text}
        Desired Role: {preferences.get('desired_role', '')}
        Preferred Industries: {', '.join(preferences.get('industries', []))}
        Preferred Locations: {', '.join(preferences.get('locations', []))}
        """
        return search_text.strip()

    def _evaluate_match(self, resume_text: str, startup_info: str, preferences: Dict) -> Dict:
        """Score match using LLM"""
        prompt = """
        You are evaluating a match between a candidate and a startup.

        First, extract the company name and create a brief description from this potentially unstructured startup information:
        {}

        Then evaluate this startup against:

        RESUME:
        {}

        CANDIDATE PREFERENCES:
        Desired Role: {}
        Preferred Industries: {}
        Preferred Locations: {}
        Preferred Company Stages: {}

        Evaluate this match using these steps:

        Step 1: Industry Match (35%)
        - Score 1.0: Exact industry match
        - Score 0.7: Adjacent industry match
        - Score 0.5: Same sector different focus
        - Score 0.0: Different industry

        Step 2: Technical Skills Match (25%)
        - Score 1.0: Core skills direct match
        - Score 0.7: Related skills match
        - Score 0.5: Foundational skills match
        - Score 0.0: No technical skills match

        Step 3: Experience Level Match (25%)
        For startup stage:
        - Mature Stage (50+ employees): 15+ years ideal
        - Growth Stage (11-50 employees): 6-12 years ideal
        - Early Stage (1-10 employees): 0-5 years ideal
        Score accordingly.

        Step 4: Growth Stage Match (15%)
        - Score 1.0: Full growth match
        - Score 0.7: Partial growth match
        - Score 0.5: Basic growth understanding
        - Score 0.0: No growth match

        Return ONLY a valid JSON object with no additional text, using this exact format:
        {{
            "company_name": "<extracted company name>",
            "company_description": "<brief 1-2 sentence description>",
            "industry_score": <float between 0 and 1>,
            "technical_score": <float between 0 and 1>,
            "experience_score": <float between 0 and 1>,
            "growth_score": <float between 0 and 1>,
            "final_score": <weighted average as float>,
            "reasoning": "<brief explanation as string>"
        }}
        """.format(
            startup_info,
            resume_text,
            preferences.get('desired_roles', []),
            preferences.get('industries', []),
            preferences.get('work_locations', []),
            preferences.get('company_stages', [])
        )

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert recruiter evaluating candidate-startup matches. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3  # Lower temperature for more consistent JSON output
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {str(e)}")
            print(f"Raw response: {response.choices[0].message.content}")
            return {
                "error": "Failed to parse LLM response",
                "raw_response": response.choices[0].message.content
            }

    def get_company_matches(self, resume_text: str, preferences: Dict, num_matches: int = 1, min_score: float = 0.6) -> List[Dict]:
        print("\nDEBUG: Starting company matches search...")
        
        # Prepare search text
        search_text = self._prepare_search_text(resume_text, preferences)
        print(f"DEBUG: Search text prepared: {search_text[:100]}...")
        
        # Generate embedding
        query_embedding = self._create_embedding(search_text)
        print("DEBUG: Generated embedding")
        
        # Search ChromaDB
        initial_matches = num_matches * 2
        print(f"DEBUG: Searching for {initial_matches} initial matches...")
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=initial_matches
        )
        print(f"DEBUG: Results: {results}")
        print(f"DEBUG: Found {len(results['documents'][0])} documents")
        
        # Process and score matches
        scored_matches = []
        for idx, company in enumerate(results['documents'][0]):
            print(f"\nDEBUG: Evaluating match {idx + 1}")
            #print(f"DEBUG: Company: {company}")
            # Get LLM evaluation
            evaluation = self._evaluate_match(
                resume_text=resume_text,
                startup_info=company,
                preferences=preferences
            )
            print(f"DEBUG: Evaluation result: {evaluation}")
            
            # Only include matches that meet the minimum score threshold
            if evaluation.get('final_score', 0) >= min_score:
                match_data = {
                    'startup_id': results['metadatas'][0][idx].get('startup_id'),
                    'final_score': evaluation['final_score'],
                    'company_name': evaluation['company_name'],
                    'company_description': evaluation['company_description'],
                    'similarity_score': results['distances'][0][idx],
                    'startup_info': company,
                    'match_reasons': {
                        'industry_match': evaluation['industry_score'],
                        'technical_match': evaluation['technical_score'],
                        'experience_match': evaluation['experience_score'],
                        'growth_match': evaluation['growth_score'],
                        'reasoning': evaluation['reasoning']
                    },
                    'metadata': results['metadatas'][0][idx]
                }
                scored_matches.append(match_data)
                print(f"DEBUG: Added match with score {evaluation['final_score']}")
            else:
                print(f"DEBUG: Match below threshold ({min_score}), skipping")
        
        print(f"\nDEBUG: Total matches before sorting: {len(scored_matches)}")
        # Sort by final_score and limit to requested number of matches
        scored_matches.sort(key=lambda x: x['final_score'], reverse=True)
        scored_matches = scored_matches[:num_matches]
        print(f"DEBUG: Final matches after filtering: {len(scored_matches)}")
        
        response = {
            'matches': scored_matches,
            'count': len(scored_matches),
            'min_score_applied': min_score
        }
        print(f"DEBUG: Final response structure: {list(response.keys())}")
        return response 