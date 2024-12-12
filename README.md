# Startup Explorer Service

A service that matches candidates with startups based on their resume and preferences using AI-powered matching.

## Features

- Resume parsing and analysis
- Candidate preference collection
- AI-powered matching using OpenAI embeddings and GPT-4
- Vector similarity search using ChromaDB
- Intelligent scoring system considering:
  - Industry match (35%)
  - Technical skills match (25%)
  - Experience level match (25%)
  - Growth stage match (15%)

## Setup

1. Clone the repository:
```bash
git clone https://github.com/startup-explorer/startup-explorer-service.git
```

2. Navigate to the project directory:
```bash
cd startup-explorer-service
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
```

5. Run the service:
```bash
python app.py
```

6. Access the API documentation at:
```bash
http://localhost:8000/docs
```

## API Endpoints

### 1. Upload Resume
- **Endpoint**: `/uploadResume`
- **Method**: POST
- **Input**: PDF file
- **Returns**: Session ID for the matching process

### 2. Submit Preferences
- **Endpoint**: `/submitPreferences`
- **Method**: POST
- **Input**: JSON with preferences including:
  - desired_roles
  - industries
  - work_locations
  - company_stages
- **Returns**: Success confirmation

### 3. Get Matches
- **Endpoint**: `/api/matches`
- **Method**: GET
- **Parameters**: session_id
- **Returns**: JSON with matched companies including:
  - Company name and description
  - Match scores and reasoning
  - Similarity metrics
  - Detailed match reasons

## Testing

Run the integration tests:
```bash
python -m test/test_matching_flow.py
```


The tests will:
1. Upload a test resume
2. Submit sample preferences
3. Retrieve and display matches
4. Test error cases

## Match Scoring

The matching algorithm evaluates candidates based on:
- Industry alignment
- Technical skill compatibility
- Experience level appropriateness
- Company growth stage fit

Each match includes:
- Extracted company name and description
- Final score (weighted average)
- Individual category scores
- Detailed reasoning for the match

## Notes

- Ensure your OpenAI API key has sufficient credits
- The ChromaDB path should be accessible and writable
- Test resume should be placed in the test directory
- Sensitive files (API keys, test data) are git-ignored

## Environment Variables

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `CHROMA_DB_PATH`: Path to ChromaDB storage (default: "/Users/ananth/startup-explorer/chroma_db")

