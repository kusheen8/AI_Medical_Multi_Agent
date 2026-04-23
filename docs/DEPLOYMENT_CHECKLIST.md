# Production Deployment Readiness Checklist

- **Environment Config**: Valid `.env` with strong JWT passwords, proper external API tokens.
- **HTTPS & Certificates**: Let's Encrypt certificates valid and deployed.
- **MongoDB Encryption**: Field-level encryption active; storage encryption verified in remote provider.
- **CORS Config**: `CORS_ALLOWED_ORIGINS` tightly mapped to `frontend_domain` in production config.
- **Log Management**: Standard structured JSON logs fed into Datadog/CloudWatch. Level set to `INFO`.
- **RBAC Active**: `REQUIRE_AUTH=True` enabled in `.env`.
- **Ollama Models Cached**: The `medgemma:4b` model is running and pre-warmed.
- **API Rate Limits**: Defined to 100/min login and 1000/min overall to prevent DoS.
- **Tracing Disabled/Enabled**: Sample tracing output rate configured correctly (default 10%).

All checks must clear before signing off `Production` tags.
