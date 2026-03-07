## Integration checks for React + Three.js

- Enable CORS in FastAPI for your frontend origin.
- Define strict JSON contracts with Pydantic models for scene/agent state payloads.
- Decide realtime channel early (WebSocket for live updates, SSE for streaming text - events).

## Pinned Frontend/Backend Version Matrix

| Layer | Package | Pinned Version | Why this pin | Upgrade rule |
|---|---|---:|---|---|
| Frontend Core | react | 18.3.1 | Stable with current R3F v8 line | Upgrade only with react-dom + full UI regression pass |
| Frontend Core | react-dom | 18.3.1 | Must match React major/minor | Keep exactly equal to react |
| 3D Engine | three | 0.173.0 | Modern Three release with broad R3F v8 compatibility | Bump only after checking R3F peer dependency notes |
| React Renderer for Three | @react-three/fiber | 8.17.14 | Mature v8 branch for React 18 | Upgrade in lockstep with Three compatibility check |
| Backend API | fastapi | 0.135.1 | Already pinned in backend requirements | Bump with Starlette/Pydantic smoke tests |

### Safe lock policy for team

- Frontend: commit `package-lock.json` and install with `npm ci` in CI/local onboarding.
- Backend: keep exact `==` pins in `requirements.txt` and install with `pip install -r requirements.txt`.
- Do not use caret (`^`) or tilde (`~`) for the matrix packages.
- Upgrade cadence: one dependency family at a time (`React stack`, `Three/R3F stack`, `FastAPI stack`).

### Example install pins (frontend)

```bash
npm install --save-exact react@18.3.1 react-dom@18.3.1 three@0.173.0 @react-three/fiber@8.17.14
```

### Optional: stricter backend reproducibility

If you want fully reproducible backend builds across OS/Python patch versions, generate a lock file with hashes:

```bash
pip install pip-tools
pip-compile --generate-hashes -o requirements.lock.txt requirements.txt
pip install --require-hashes -r requirements.lock.txt
```
