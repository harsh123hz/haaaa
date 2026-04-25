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

The simplest live deployment is one Docker web service. The Dockerfile builds the React frontend, serves it from Django/WhiteNoise, runs migrations, seeds demo data, and starts Gunicorn.

Render setup:

1. Go to Render and create `New > Web Service`.
2. Connect this GitHub repo: `https://github.com/harsh123hz/haaaa.git`.
3. Set `Language` to `Docker`.
4. Use branch `main` and root directory blank.
5. Add environment variables:
   - `DJANGO_SECRET_KEY`: any long random string
   - `DJANGO_DEBUG`: `0`
   - `DJANGO_ALLOWED_HOSTS`: `.onrender.com,localhost,127.0.0.1`
6. Create the service and wait for deploy to finish.

The live URL will serve both the frontend and API:

- Frontend: `https://your-service.onrender.com/`
- API: `https://your-service.onrender.com/api/v1/`

Seeded login tokens on the live service are the same:

- `merchant-draft-token`
- `merchant-review-token`
- `reviewer-token`

This demo uses SQLite inside the service container. That is fine for the assignment poke-around flow, but production should use Postgres and object storage for uploaded documents.
