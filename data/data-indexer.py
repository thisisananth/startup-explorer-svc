import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import chromadb
from chromadb.config import Settings
import spacy
from bs4 import BeautifulSoup
import unicodedata
import PyPDF2
from pathlib import Path
import logging
from tqdm import tqdm
import json
import openai
from dotenv import load_dotenv
import hashlib
from tenacity import retry, wait_exponential, stop_after_attempt
from datetime import datetime
import re 

# Load environment variables
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('press_release_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ProcessedDocument:
    clean_text: str
    key_sections: Dict[str, str]
    extracted_entities: Dict[str, List[str]]
    metadata: Dict[str, any]

class PDFExtractor:
    """Handles PDF document extraction"""
    
    @staticmethod
    def extract_text_from_pdf(pdf_path: Path) -> str:
        """Extract text content from PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ' '.join(page.extract_text() for page in pdf_reader.pages)
                print(text)
                return text
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
            return ""

class PressReleasePreprocessor:
    """Handles press release text preprocessing and metadata extraction"""
    
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.patterns = {
            'image_captions': r'\(([^)]*(?:Image|Photo|Screenshot)[^)]*)\)',
            'urls': r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            'email': r'\S+@\S+',
            'multiple_spaces': r'\s+',
            'special_chars': r'[^\w\s.,!?-]'
        }
        self.section_keywords = {
            'company_description': [
                'about', 'company', 'startup', 'founded', 'headquarters', 
                'based', 'mission', 'vision'
            ],
            'product_details': [
                'product', 'platform', 'solution', 'technology', 'features',
                'capabilities', 'launches', 'introducing'
            ],
            'technical_info': [
                'technical', 'technology', 'stack', 'architecture', 'built with',
                'powered by', 'infrastructure', 'AI', 'ML', 'algorithm'
            ],
            'team_info': [
                'founder', 'ceo', 'team', 'leadership', 'executive',
                'previously worked', 'background'
            ],
            'funding_info': [
                'funding', 'raised', 'investment', 'investors', 'round',
                'seed', 'series', 'led by', 'participated'
            ]
        }

    def clean_html(self, text: str) -> str:
        """Remove HTML tags and clean up HTML entities"""
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text(separator=' ')

    def normalize_text(self, text: str) -> str:
        """Normalize unicode characters and whitespace"""
        # Normalize unicode
        text = unicodedata.normalize('NFKD', text)
        
        # Replace multiple spaces with single space
        text = re.sub(self.patterns['multiple_spaces'], ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(self.patterns['special_chars'], '', text)
        
        return text.strip()

    def remove_boilerplate(self, text: str) -> str:
        """Remove common press release boilerplate content"""
        # Remove image captions
        text = re.sub(self.patterns['image_captions'], '', text)
        
        # Remove URLs
        text = re.sub(self.patterns['urls'], '', text)
        
        # Remove email addresses
        text = re.sub(self.patterns['email'], '', text)
        
        # Remove common press release endings
        text = re.sub(r'(?i)For more information.*$', '', text)
        text = re.sub(r'(?i)About .*\n.*$', '', text)
        
        return text.strip()

    def clean_text(self, text: str) -> str:
        """Combine all text cleaning steps"""
        text = self.clean_html(text)
        text = self.normalize_text(text)
        text = self.remove_boilerplate(text)
        return text.strip()

    def extract_sections(self, text: str) -> Dict[str, str]:
        """Extract specific sections based on keywords"""
        doc = self.nlp(text)
        sections = {}
        
        # Split into sentences
        sentences = list(doc.sents)
        
        for section_type, keywords in self.section_keywords.items():
            relevant_sentences = []
            for i, sent in enumerate(sentences):
                sent_text = sent.text.lower()
                
                # Check if sentence contains relevant keywords
                if any(keyword in sent_text for keyword in keywords):
                    # Include the sentence and potentially the next one for context
                    relevant_sentences.append(sent.text)
                    if i + 1 < len(sentences):
                        relevant_sentences.append(sentences[i + 1].text)
            
            if relevant_sentences:
                sections[section_type] = ' '.join(relevant_sentences).strip()
                
        return sections

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from the text"""
        doc = self.nlp(text)
        entities = {
            'organizations': [],
            'people': [],
            'locations': [],
            'products': [],
            'amounts': []
        }
        
        for ent in doc.ents:
            if ent.label_ == 'ORG':
                entities['organizations'].append(ent.text)
            elif ent.label_ == 'PERSON':
                entities['people'].append(ent.text)
            elif ent.label_ == 'GPE':
                entities['locations'].append(ent.text)
            elif ent.label_ == 'PRODUCT':
                entities['products'].append(ent.text)
            elif ent.label_ in ['MONEY', 'CARDINAL']:
                entities['amounts'].append(ent.text)
        
        # Remove duplicates while preserving order
        for key in entities:
            entities[key] = list(dict.fromkeys(entities[key]))
            
        return entities

    def generate_metadata(self, text: str, sections: Dict[str, str], entities: Dict[str, List[str]]) -> Dict:
        """
        Generate metadata from the processed text.
        Ensures all values are ChromaDB-compatible (str, int, float, or bool)
        """
        doc = self.nlp(text)
        
        metadata = {
            'word_count': len(text.split()),
            'sentence_count': len(list(doc.sents)),
            'has_technical_info': bool(sections.get('technical_info')),
            'has_funding_info': bool(sections.get('funding_info')),
            # Convert lists to comma-separated strings
            'mentioned_organizations': ','.join(entities['organizations']) if entities['organizations'] else '',
            'mentioned_people': ','.join(entities['people']) if entities['people'] else '',
            'mentioned_locations': ','.join(entities['locations']) if entities['locations'] else '',
            'section_present': ','.join(key for key, value in sections.items() if value),
            'extracted_amounts': ','.join(entities['amounts']) if entities['amounts'] else '',
            # Add section content as strings
            'company_description': sections.get('company_description', ''),
            'product_details': sections.get('product_details', ''),
            'technical_info': sections.get('technical_info', ''),
            'team_info': sections.get('team_info', ''),
            'funding_info': sections.get('funding_info', '')
        }
        
        return metadata

    def clean_and_preprocess(self, text: str) -> ProcessedDocument:
        """Main preprocessing pipeline"""
        # Clean the text
        clean_text = self.clean_text(text)
        
        # Extract sections
        sections = self.extract_sections(clean_text)
        
        # Extract entities
        entities = self.extract_entities(clean_text)
        
        # Generate metadata (compatible with ChromaDB)
        metadata = self.generate_metadata(clean_text, sections, entities)
        
        return ProcessedDocument(
            clean_text=clean_text,
            key_sections=sections,
            extracted_entities=entities,
            metadata=metadata
        )

class OpenAIEmbeddings:
    """Handles creation of embeddings using OpenAI's API"""
    
    @retry(wait=wait_exponential(min=1, max=60), stop=stop_after_attempt(5))
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding using OpenAI's ada-002 model"""
        try:
            response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            raise

class ChromaDBManager:
    """Manages ChromaDB operations"""
    
    def __init__(self, 
                 collection_name: str,
                 persist_dir: str = "./chroma_db",
                 is_persistent: bool = True):
        if is_persistent:
            self.client = chromadb.PersistentClient(
                path=persist_dir
            )
        else:
            self.client = chromadb.HttpClient(
                host="localhost",
                port=8000
            )
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def _sanitize_metadata(self, metadata: Dict) -> Dict:
        """Ensure metadata only contains ChromaDB-compatible types"""
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list):
                sanitized[key] = ','.join(str(v) for v in value)
            elif value is None:
                sanitized[key] = ''
            else:
                sanitized[key] = str(value)
        return sanitized

    def store_document(self, 
                      doc_id: str, 
                      embedding: List[float], 
                      metadata: Dict, 
                      text: str):
        """Store document in ChromaDB"""
        try:
            # Sanitize metadata before storing
            clean_metadata = self._sanitize_metadata(metadata)
            
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[clean_metadata],
                documents=[text]
            )
        except Exception as e:
            logger.error(f"Error storing document {doc_id}: {str(e)}")
            raise

class PressReleaseProcessor:
    """Main class orchestrating the press release processing pipeline"""
    
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.preprocessor = PressReleasePreprocessor()
        self.embeddings = OpenAIEmbeddings()
        self.db = ChromaDBManager("startup_press_releases")
        
    def generate_doc_id(self, file_path: str, content: str) -> str:
        """Generate a unique document ID"""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{Path(file_path).stem}_{content_hash[:8]}"

    def process_single_document(self, pdf_path: Path) -> Optional[str]:
        """Process a single press release document"""
        try:
            # Extract text from PDF
            raw_text = self.pdf_extractor.extract_text_from_pdf(pdf_path)
            if not raw_text:
                return None

            # Generate document ID
            doc_id = self.generate_doc_id(str(pdf_path), raw_text)

            # Preprocess text
            processed_doc = self.preprocessor.clean_and_preprocess(raw_text)

            # Create embedding
            embedding = self.embeddings.create_embedding(processed_doc.clean_text)

            # Prepare metadata
            metadata = {
                "filename": pdf_path.name,
                "processed_date": str(datetime.now()),
                **processed_doc.metadata,
                "entities": processed_doc.extracted_entities
            }

            # Store in ChromaDB
            self.db.store_document(
                doc_id=doc_id,
                embedding=embedding,
                metadata=metadata,
                text=processed_doc.clean_text
            )

            return doc_id

        except Exception as e:
            logger.error(f"Error processing document {pdf_path}: {str(e)}")
            return None

    def process_directory(self, directory_path: str):
        """Process all PDF files in a directory"""
        pdf_files = list(Path(directory_path).glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files to process")

        processed_ids = []
        with tqdm(total=len(pdf_files)) as pbar:
            for pdf_path in pdf_files:
                doc_id = self.process_single_document(pdf_path)
                if doc_id:
                    processed_ids.append(doc_id)
                pbar.update(1)

        logger.info(f"Successfully processed {len(processed_ids)} documents")
        return processed_ids

def main():
    """Main execution function"""
    try:
        # Initialize processor
        processor = PressReleaseProcessor()
        
        # Process all documents in the specified directory
        input_directory = "./docs"
        processed_ids = processor.process_directory(input_directory)
        
        # Save processing results
        with open('processing_results.json', 'w') as f:
            json.dump({
                'processed_documents': processed_ids,
                'timestamp': str(datetime.now())
            }, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()