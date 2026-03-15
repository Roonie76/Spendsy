# Contributing to Spendsy

First off, thank you for considering contributing to Spendsy! It's people like you that make the open-source community such a great place to stay, learn, and create.

## 🚀 How Can I Help?

### Reporting Bugs
If you find a bug, please open an issue and include:
- A clear description of the problem.
- Steps to reproduce.
- Expected vs actual behavior.
- Environment details (Browser, OS, Docker version).

### Suggesting Enhancements
We love new ideas! If you have a feature request:
- Check if it's already been suggested in the issues.
- Explain Why this feature would be useful.

### Pull Requests
1. Fork the repo and create your branch from `main`.
2. Follow the existing code style (PEP 8 for Python, Prettier for JS).
3. Ensure all tests pass (`pytest` and `vitest`).
4. Keep your PR small and focused on a single change.

## 🛠️ Development Setup

### Backend (Python)
We use a unified `requirements.txt` at the root, but each service also manages its own for containerization.
```bash
# Unified setup (recommended)
pip install -r requirements.txt

# Or per-service
cd spendsy/services/finance-service
pip install -r requirements.txt
pytest
```

### Frontend (React)
```bash
cd apps/web/frontend
npm install
npm run dev
```

### Docker (Preferred)
```bash
docker compose -f infra/docker/docker-compose.dev.yml up --build
```

## 📜 Code Style & Reliability Guidelines
- **Python**: Use type hints, Pydantic for schemas, and docstrings for public functions. 
- **Reliability**: 
    - All inter-service calls MUST use `tenacity` retries and explicit timeouts.
    - All database commits MUST be wrapped in `try/except` with `db.rollback()`.
    - Avoid direct DB connections; always use the PgBouncer-pooled session.
- **Javascript/React**: Use functional components, hooks, and descriptive variable names. Always use the `apiFetch` wrapper for network requests.
- **Commit Messages**: Follow [Conventional Commits](https://www.conventionalcommits.org/).

## ⚖️ License
By contributing, you agree that your contributions will be licensed under the MIT License.
