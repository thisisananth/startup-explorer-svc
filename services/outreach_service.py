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

    def _generate_cover_letter(self, resume_text: str, company_info: Dict, role: str) -> str:
        prompt = f"""
        Write a professional cover letter for a job application based on the following information.
        Do not include the date or company address. Start directly with "Dear Hiring Manager," 
        
        RESUME:
        {resume_text}

        COMPANY:
        {company_info['company_name']}
        {company_info.get('company_description', '')}
        Industry: {company_info.get('industry', 'Technology')}

        DESIRED ROLE:
        {role}

        Write a concise, compelling cover letter that:
        1. Shows enthusiasm for the company and role
        2. Highlights relevant experience from the resume
        3. Demonstrates understanding of the company's business
        4. Explains why you're a good fit
        5. Ends with a professional closing

        Keep the tone professional but conversational.
        """

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert at writing compelling cover letters."},
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
        cover_letter = self._generate_cover_letter(
            resume_text,
            company_info,
            role_preference
        )
        
        return {
            "contacts": contacts,
            "cover_letter": cover_letter,
            "company_info": company_info
        } 