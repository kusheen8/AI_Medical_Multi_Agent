#!/usr/bin/env python3
"""Quick test to verify MedGemma is working properly"""

import requests
import json
import time
import logging
from datetime import datetime

OLLAMA_URL = "http://localhost:11434"
MODEL = "MedAIBase/MedGemma1.5:4b"

# Configure logging
LOG_FILE = f"medgemma_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

def test_medgemma():
    """Test medgemma with medical queries"""
    
    logger.info("=" * 60)
    logger.info("MedGemma Diagnostic Test")
    logger.info("=" * 60)
    
    # Test 1: Check if Ollama is running
    logger.info("\n[1] Checking Ollama connection...")
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = response.json()
        logger.info(f"✓ Ollama is running")
        logger.info(f"✓ Available models: {len(models.get('models', []))}")
        for model in models.get('models', []):
            logger.info(f"  - {model['name']} ({model['details']['parameter_size']})")
    except Exception as e:
        logger.error(f"✗ Failed to connect to Ollama: {e}")
        return False
    
    # Test 2: Simple medical query
    logger.info("\n[2] Testing medical query...")
    try:
        start_time = time.time()
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": "List 3 common symptoms of hypertension.",
                "stream": False,
                "temperature": 0.3  # Low temperature for consistent medical answers
            },
            timeout=120
        )
        elapsed = time.time() - start_time
        
        result = response.json()
        logger.info(f"✓ Model responded in {elapsed:.2f} seconds")
        logger.info(f"\nResponse preview:")
        logger.info(result.get('response', 'No response')[:200] + "...")
        logger.info(f"\nFull metrics:")
        logger.info(f"  - Total duration: {result.get('total_duration', 'N/A')} ns")
        logger.info(f"  - Load duration: {result.get('load_duration', 'N/A')} ns")
        logger.info(f"  - Prompt eval count: {result.get('prompt_eval_count', 'N/A')}")
        logger.info(f"  - Eval count: {result.get('eval_count', 'N/A')}")
        
    except requests.exceptions.Timeout:
        logger.error("✗ Request timed out - model may be loading")
        return False
    except Exception as e:
        logger.error(f"✗ Failed to query model: {e}")
        return False
    
    # Test 3: Entity extraction (medical function)
    logger.info("\n[3] Testing medical entity extraction...")
    try:
        start_time = time.time()
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": """Extract medical entities from: "Patient reports persistent headache, fever of 102F, and fatigue for 3 days."
Format as: Symptoms: [...], Duration: [...], Severity: [...]""",
                "stream": False,
                "temperature": 0.2
            },
            timeout=120
        )
        elapsed = time.time() - start_time
        
        result = response.json()
        logger.info(f"✓ Entity extraction completed in {elapsed:.2f} seconds")
        logger.info(f"\nExtracted entities:")
        logger.info(result.get('response', 'No response'))
        
    except Exception as e:
        logger.error(f"✗ Failed entity extraction test: {e}")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ All tests passed! MedGemma is running properly.")
    logger.info("=" * 60)
    logger.info(f"\nLog file saved to: {LOG_FILE}")
    return True

if __name__ == "__main__":
    test_medgemma()
