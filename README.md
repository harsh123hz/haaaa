# Playto KYC Pipeline

A small Django/DRF plus React/Tailwind implementation of Playto Pay's merchant KYC onboarding and reviewer workflow.

## What is included

- Merchant signup, draft saving, document upload, and submit-for-review.
- Reviewer dashboard with oldest-first queue, dynamic 24 hour SLA flag, and 7 day approval metrics.
- Centralized state machine for `draft -> submitted -> under_review -> approved/rejected/more_info_requested`.
- File validation using size, extension, and magic-byte checks for PDF, JPG, and PNG.
- Token auth with merchant/reviewer roles.
- Notification events logged on every state transition.
- Seed command and API tests.

## Backend setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd backend
python manage.py migrate
python manage.py seed_kyc
python manage.py runserver
```

The API runs at `http://localhost:8000/api/v1/`.

Seeded tokens:

- `merchant-draft-token`
- `merchant-review-token`
- `reviewer-token`

Use them as `Authorization: Token <token>`.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The token switcher has the seeded users prefilled.

Set `VITE_API_BASE_URL` if the API is not at `http://localhost:8000/api/v1`.

## Tests

```bash
cd backend
python manage.py test
```

The tests cover illegal state transitions, missing documents on submit, upload signature validation, and a successful reviewer start-review transition.

## Main API endpoints

- `POST /api/v1/auth/signup/`
- `GET /api/v1/auth/me/`
- `GET/PATCH /api/v1/merchant/submission/`
- `POST /api/v1/merchant/submission/documents/`
- `POST /api/v1/merchant/submission/submit/`
- `GET /api/v1/merchant/notifications/`
- `GET /api/v1/reviewer/dashboard/`
- `GET /api/v1/reviewer/submissions/<id>/`
- `POST /api/v1/reviewer/submissions/<id>/transition/`

Reviewer transition body:

```json
{
  "action": "approve",
  "reason": "Documents match submitted details."
}
```

Valid actions are `start_review`, `approve`, `reject`, and `request_more_info`.

## Deployment notes

This repo is ready for a free split deployment: backend on Render/Railway/Fly with SQLite or Postgres, frontend on Vercel/Netlify. Run `python manage.py migrate && python manage.py seed_kyc` on the backend service before sharing the URL.

I could not create a live deployment from this local workspace because no provider credentials were available.

