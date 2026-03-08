# DEPRECATED

The `backend/` directory has been flattened to the repository root.

New locations:
- `backend/main.py` -> `main.py`
- `backend/config.py` -> `config.py`
- `backend/requirements.txt` -> `requirements.txt`
- `backend/Dockerfile` -> `Dockerfile`
- `backend/auth/` -> `auth/`
- `backend/routers/` -> `routers/`
- `backend/services/` -> `services/`

To clean up:

```bash
git rm -r backend/
git commit -m "chore: remove deprecated backend/ directory (flattened to root)"
```
