# Multi-Agent Medical Support System (Hybrid AI Edition)

A **hybrid multi-agent system** powered by local and cloud-based LLMs, designed to assist **elderly and chronically ill patients** with privacy-first medical guidance and coordination.

>  **Disclaimer:** This project is for educational purposes only. Local medical analysis is performed by MedGemma and does not replace professional clinical judgment.

---

## Problem Statement
Elderly patients require constant monitoring and medication adherence, yet sharing sensitive health data with cloud providers often raises privacy concerns. This project addresses the gap between **AI capability** and **data sovereignty**.

---

## Project Objective
To build a single-interface system where specialized agents collaborate using a **Hybrid Inference Pipeline**:
- **Privacy-First:** Local processing of sensitive symptoms and medical history.
- **Intelligent Routing:** High-level task coordination via cloud-based reasoning.
- **Real-time Support:** Proactive reminders and caregiver alerts.

---

## System Architecture & Agent Roles

The system utilizes a split-brain approach to balance performance on local hardware (RTX 3070 Ti) with cloud intelligence.

### Cloud Agents (Gemini 1.5 Flash)
- **LLM Coordinator Agent:** The central router that determines user intent and delegates tasks.
- **Caregiver Notification Agent:** Logic-heavy agent that manages emergency alerts and communication.

### Local Agents (MedGemma 4B via Ollama)
- **Medical Analyzer Agent:** Performs clinical entity extraction and symptom analysis locally to ensure patient data never leaves the device.
- **History Summarizer:** Processes long-term patient logs to identify health trends without cloud exposure.

---

## Technologies Used
- **LLMs:** Gemini 1.5 Flash (API) & MedGemma 4B (Local via Ollama).
- **Backend:** FastAPI (Python) with asynchronous task handling.
- **Database:** MongoDB with Motor (Async driver).
- **Optimization:** Q4_K_M Quantization for local inference on 8GB VRAM.

---

## Environment Setup
 
1. Create your local env file from the template:
 	- `cp .env.example .env` (Linux/macOS)
 	- `copy .env.example .env` (Windows CMD)
 	- `Copy-Item .env.example .env` (PowerShell)
 2. Fill in `GEMINI_API_KEY` from Google AI Studio.
 3. Fill in `MONGODB_URI` from your MongoDB Atlas connection string.
 4. Make sure Ollama is running locally at `http://localhost:11434` and the model in `OLLAMA_MODEL` is pulled.
 
 Minimum required values to run this stack:
 - `GEMINI_API_KEY`
 - `MONGODB_URI`
 - `OLLAMA_BASE_URL`
 - `OLLAMA_MODEL`
 
 ---
 
 ## Local Model Testing
 - Test MedGemma 4B integration: `python backend/test_medgemma.py`
 - This verifies Ollama connectivity and model responsiveness
 
 ---
 
 ## Implementation Progress
 - [ ] Multi-agent architecture finalized.
 - [ ] Local MedGemma 4B integration (Ollama).
 - [ ] Pydantic data schemas for Patients & Medications.
 - [ ] Hybrid routing logic (Gemini Coordinator <-> MedGemma).
 - [ ] UI & Frontend integration.
 
 ---
 
 ## Future Enhancements
 - Voice-based interaction
 - Emergency alert system
 - Wearable device integration
 - Multilingual support
 
 ---
 
 ## Team
 - Kusheen Dhar   
 - Rida Fatima
 - Samim Kausar
 - Pawan T Singh
 
 ---
 
 ## License
 Academic coursework project - Developed at Nitte Meenakshi Institute of Technology.
