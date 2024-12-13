from openai import OpenAI
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

class OutreachService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_sample_contacts(self, company_info: Dict, role_preference: str) -> List[Dict]:
        """Generate realistic but fictional sample contacts using GPT-4"""
        
        prompt = f"""
        Generate 2 realistic but fictional contacts for this company:
        
        Company Name: {company_info.get('company_name')}
        Company Description: {company_info.get('company_description')}
        Industry: {company_info.get('industry', 'Technology')}
        Candidate's Target Role: {role_preference}

        For each contact, provide:
        1. A realistic full name
        2. A relevant senior role that would be involved in hiring for {role_preference}
        3. A fictional but realistic business email

        Return ONLY a valid JSON array with 2 contacts, using this exact format:
        [
            {{
                "name": "Full Name",
                "role": "Job Title",
                "email": "business_email@company.com"
            }},
            {{
                "name": "Full Name",
                "role": "Job Title",
                "email": "business_email@company.com"
            }}
        ]
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at generating realistic but fictional business contacts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            import json
            contacts = json.loads(response.choices[0].message.content)
            return contacts
            
        except Exception as e:
            print(f"Error generating contacts: {str(e)}")
            # Return fallback contacts if generation fails
            return [
                {
                    "name": "John Smith",
                    "role": "Engineering Manager",
                    "email": f"jsmith@{company_info.get('company_name', 'company').lower().replace(' ', '')}.com"
                },
                {
                    "name": "Sarah Johnson",
                    "role": "Technical Recruiter",
                    "email": f"sjohnson@{company_info.get('company_name', 'company').lower().replace(' ', '')}.com"
                }
            ]

    def generate_cover_letter(self, 
                            resume_text: str, 
                            company_info: Dict,
                            role_preference: str) -> str:
        """
        Generate a customized cover letter using GPT-4
        """
        prompt = f"""
        Write a compelling cover letter based on this information:

        RESUME:
        {resume_text}

        COMPANY:
        Name: {company_info.get('company_name')}
        Description: {company_info.get('company_description')}
        Industry: {company_info.get('industry')}

        DESIRED ROLE: {role_preference}

        Write a professional cover letter that:
        1. Shows genuine interest in the company's mission
        2. Connects the candidate's experience to the company's needs
        3. Highlights relevant achievements from the resume
        4. Demonstrates knowledge of the company
        5. Keeps the tone professional but enthusiastic
        6. Is concise (250-300 words)

        Format the letter properly with today's date and proper business letter structure.
        """

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert at writing compelling cover letters that help candidates stand out."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content

    def get_outreach_package(self, 
                           resume_text: str, 
                           company_info: Dict,
                           role_preference: str) -> Dict:
        """
        Generate complete outreach package including contacts and cover letter
        """
        # Generate sample contacts
        contacts = self.generate_sample_contacts(
            company_info,
            role_preference
        )
        
        # Generate cover letter
        cover_letter = self.generate_cover_letter(
            resume_text,
            company_info,
            role_preference
        )
        
        return {
            "contacts": contacts,
            "cover_letter": cover_letter,
            "company_info": company_info
        } 