# Operational Runbooks

## 1. Graceful Startup/Shutdown
- **Startup**: 
  1. Boot database (`MongoDB`).
  2. Boot Ollama Models (`Ollama pull medgemma:4b`).
  3. Start FastAPI `uvicorn app.main:app --workers 4`.
- **Shutdown**: Send SIGTERM to Uvicorn. The `lifespan` context guarantees wait times for ongoing queue tasks before yielding process termination.

## 2. Certificate Renewal
We utilize Let's Encrypt bot for automated HTTPS renewals.
Manual forced renewal:
`certbot renew --force-renewal`
Restart Nginx/Proxy: `systemctl reload nginx`

## 3. High Error Rate / Worker Scaling
Symptom: Queue depth consistently > 500 tasks.
Action: 
- Check metrics via `/api/v1/metrics` for queue length.
- Scale background workers horizontally by scaling the deployed container replicas up by exactly N+2.

## 4. Ollama Model Outage
Symptom: Circuit Breaker trips for the Ollama integration. MedGemma models failing to load.
Action:
- The system will naturally pause processing from the Queue logic and wait linearly utilizing the Delay handler. Do NOT manually intervene unless the host box indicates RAM/GPU exhaustion.
