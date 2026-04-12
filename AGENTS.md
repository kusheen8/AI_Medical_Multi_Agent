# AI Medical Multi-Agent Agent Guidelines

## Environment Setup
- Copy `.env.example` to `.env` and fill in required values:
  - `GEMINI_API_KEY` (from Google AI Studio)
  - `MONGODB_URI` (MongoDB Atlas connection string)
  - `OLLAMA_BASE_URL` (default: http://localhost:11434)
  - `OLLAMA_MODEL` (default: medgemma:4b)
- Ensure Ollama is running locally with the specified model pulled

## Local Model Testing
- Test MedGemma 4B integration: `python test_medgemma.py`
- This verifies Ollama connectivity and model responsiveness

## Important Notes
- Motor MongoDB driver is deprecated (will be removed May 14, 2026) - consider migrating to PyMongo Async driver
- Google Generative AI packages are deprecated - migrate to `google-genai` SDK
- Local agents process sensitive data via MedGemma 4B (Ollama) for privacy
- Cloud agents use Gemini 1.5 Flash for task coordination and caregiver notifications

## Project Structure
- Cloud Agents: LLM Coordinator, Caregiver Notification
- Local Agents: Medical Analyzer, History Summarizer
- Backend: FastAPI with asynchronous task handling