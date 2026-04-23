# Business Continuity and Disaster Recovery (BCDR)

## Objectives
- **RTO (Recovery Time Objective)**: < 1 Hour.
- **RPO (Recovery Point Objective)**: < 15 Minutes.

## Backup Logistics
- **Database (MongoDB)**: Automated Point-in-Time Recovery (PITR) enabled. Full snapshots captured every 12 hours. Oplog retains 24-hour continuous records. Backups are encrypted at-rest using distinct HSM keys independent of the primary cluster.
- **Artifacts**: Not applicable. AI models (`Ollama`) and `Gemini` states are completely stateless and containerized.

## Failover Mechanisms
- If the primary region goes down, DNS fails over to the standby region.
- The standby region runs cold scale-pods which auto-scale based on queue depths.
- In the event Cloud LLM (Gemini) is unavailable, the application gracefully degrades by leveraging purely local fallback logic embedded in MedGemma and notifies caregivers of reduced context analysis.

## Recovery Procedures
1. Declare disaster and trigger automated Infrastructure-as-Code (Terraform/Ansible) pipeline to deploy to Region B.
2. Restore latest MongoDB snapshot to Region B.
3. Drain the notification DLQ.
4. Verify tests pass via health endpoints (`/api/v1/health`).
5. Update DNS to shift traffic.
