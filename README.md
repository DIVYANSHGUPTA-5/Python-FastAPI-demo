# FastAPI Product Management API

A RESTful API for managing products, with JWT authentication and per-user data isolation.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063)
![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)

## Project Overview

This project is a backend API built with FastAPI that lets registered users create and manage their own products.
Users sign up, log in to receive a JWT access token, and then use that token to call the protected product endpoints.

It was built as a learning project to practise real backend fundamentals: structuring an application into routes and
services, validating data with Pydantic, authenticating users, and making sure one user can never read or change
another user's data. Storage is intentionally kept in memory so the focus stays on API design.

Concepts demonstrated: REST design and HTTP status codes, request/response schemas, password hashing, token-based
authentication, authorization (ownership checks), consistent JSON error handling, auto-generated OpenAPI docs and automated testing.

## Key Features

- 🔐 User registration and login with **JWT** authentication
- 🔑 Passwords hashed with **Argon2** (never stored in plain text)
- 👤 **User-specific products**: every product belongs to its creator
- 📦 Product CRUD: list, get, create, replace (PUT), partial update (PATCH) and delete
- 🗑️ Delete a single product, or delete **all** of the current user's products
- ✅ Input validation with Pydantic schemas and separate request/response models
- 🚦 Proper status codes and clean JSON errors (401, 404, 409, 422, 500)
- 📖 Interactive Swagger UI and ReDoc documentation
- ❤️ Health check endpoint
- 🧪 Automated tests with Pytest (40 tests)

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Python | Programming language |
| [FastAPI](https://fastapi.tiangolo.com/) | Web framework |
| [Pydantic](https://docs.pydantic.dev/) | Data validation and schemas |
| [Uvicorn](https://www.uvicorn.org/) | ASGI server |
| [PyJWT](https://pyjwt.readthedocs.io/) | Creating and verifying JWT tokens |
| [pwdlib](https://github.com/frankie567/pwdlib) (Argon2) | Password hashing |
| python-multipart | Parsing the login form (OAuth2 password flow) |
| [Pytest](https://docs.pytest.org/) + HTTPX | Automated tests with FastAPI's `TestClient` |

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                  # App creation, router registration, / and /health, error handler
│   ├── config.py                # SECRET_KEY and token settings (from environment variables)
│   ├── security.py              # Password hashing and JWT creation/decoding
│   ├── dependencies.py          # get_current_user: validates the Bearer token
│   ├── schemas.py               # Pydantic request/response models
│   ├── routes/
│   │   ├── auth.py              # POST /auth/register, POST /auth/login
│   │   └── products.py          # /products endpoints (protected)
│   └── services/
│       ├── user_service.py      # In-memory users, registration, authentication
│       └── product_service.py   # In-memory products, always filtered by owner
├── tests/
│   └── test_products.py         # Pytest test suite
├── requirements.txt
└── README.md
```

The code is split into layers: **routes** handle HTTP (status codes, errors), **services** hold the logic and storage,
**schemas** define the data contracts, and **security/dependencies** handle authentication.

## Authentication

```
Register  →  Login  →  JWT Token  →  Authorization header  →  Protected APIs
```

1. **Register**: `POST /auth/register` creates a user. The password is hashed with Argon2 before it is stored.
2. **Login**: `POST /auth/login` (form fields `username` and `password`) verifies the password and returns a signed JWT
   (HS256) that expires after 30 minutes by default. The token contains the user's ID.
3. **Authorize**: the client sends `Authorization: Bearer <token>` with each request.
4. **Protected APIs**: every `/products` endpoint depends on `get_current_user`, which validates the token and loads the
   user. A missing, invalid or expired token returns `401`.

## User Data Isolation

Each product stores the ID of the user who created it. The owner is taken **from the token**, never from the request body,
and every product operation is filtered by that user ID.

```
User 1                     User 2
 ├── Product A              ├── Product C
 └── Product B              └── Product D
```

- `GET /products` as User 1 returns only Product A and B.
- User 2 cannot read, update or delete Product A or B. Those requests return `404`, the same response as a product that does not exist, so other users' IDs are not revealed.
- `DELETE /products` as User 1 deletes only A and B; C and D remain untouched.

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth required |
|--------|----------|-------------|:-------------:|
| POST | `/auth/register` | Create a new user account | No |
| POST | `/auth/login` | Log in and receive a JWT access token | No |

### Products

| Method | Endpoint | Description | Auth required |
|--------|----------|-------------|:-------------:|
| GET | `/products` | List the current user's products | Yes |
| GET | `/products/{product_id}` | Get one of the user's products | Yes |
| POST | `/products` | Create a product owned by the current user | Yes |
| PUT | `/products/{product_id}` | Replace all fields of a product | Yes |
| PATCH | `/products/{product_id}` | Update only the fields sent | Yes |
| DELETE | `/products/{product_id}` | Delete one product | Yes |
| DELETE | `/products` | Delete all of the current user's products | Yes |

The older trailing-slash form (`/products/`) is also accepted.

### System

| Method | Endpoint | Description | Auth required |
|--------|----------|-------------|:-------------:|
| GET | `/` | API name, version and useful links | No |
| GET | `/health` | Health check | No |

## API Usage Examples

These use `curl` against `http://localhost:8001`.

**Register** (`201 Created`)

```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}'
```
```json
{"id": 1, "username": "alice"}
```

**Login** (`200 OK`). Sent as form data, not JSON.

```bash
curl -X POST http://localhost:8001/auth/login \
  -d "username=alice&password=password123"
```
```json
{"access_token": "<JWT>", "token_type": "bearer"}
```

Save the token for the next requests:

```bash
TOKEN=<paste access_token here>
```

**Create a product** (`201 Created`)

```bash
curl -X POST http://localhost:8001/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Monitor", "description": "27-inch 4K monitor", "price": 299.99, "quantity": 15}'
```
```json
{"name": "Monitor", "description": "27-inch 4K monitor", "price": 299.99, "quantity": 15, "id": 1, "user_id": 1}
```

**Get my products** (`200 OK`)

```bash
curl http://localhost:8001/products -H "Authorization: Bearer $TOKEN"
```
```json
[{"name": "Monitor", "description": "27-inch 4K monitor", "price": 299.99, "quantity": 15, "id": 1, "user_id": 1}]
```

**Delete a product** (`204 No Content`, empty body)

```bash
curl -X DELETE http://localhost:8001/products/1 -H "Authorization: Bearer $TOKEN"
```

**Delete all my products** (`200 OK`)

```bash
curl -X DELETE http://localhost:8001/products -H "Authorization: Bearer $TOKEN"
```
```json
{"deleted": 1}
```

### Field rules

| Field | Rule |
|-------|------|
| `username` | 3-50 characters, must be unique |
| `password` | 8-128 characters |
| `name` | required, 1-100 characters |
| `description` | required, up to 500 characters |
| `price` | required, `>= 0` |
| `quantity` | required, integer `>= 0` |
| `product_id` (path) | integer `> 0` |

For `PATCH`, all product fields are optional.

## Swagger Documentation

FastAPI generates interactive documentation automatically:

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

You can test every endpoint directly in Swagger UI. Register a user with `POST /auth/register`, click **Authorize**,
enter your username and password (leave `client_id` and `client_secret` empty), and the protected endpoints will use your token automatically.

## Installation

Requires Python 3.10 or newer (macOS / Linux).

```bash
git clone <your-repository-url>
cd fastapi-demo-products-get-post1

python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

## Running the Application

```bash
python -m uvicorn app.main:app --reload --port 8001
```

This starts the Uvicorn server and loads the `app` object from `app/main.py`. `--reload` restarts the server when
code changes (for development), and `--port 8001` sets the port.

## Environment Variables

Both are optional. They are read from the process environment (the app does not load a `.env` file).

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | random value generated at startup | Key used to sign JWTs |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token lifetime in minutes |

If `SECRET_KEY` is not set, tokens stop working whenever the app restarts. To use a fixed key:

```bash
export SECRET_KEY=$(openssl rand -hex 32)
python -m uvicorn app.main:app --reload --port 8001
```

No secrets are stored in the repository.

## Testing

```bash
pytest
```

The 40 tests in `tests/test_products.py` use FastAPI's `TestClient` and cover:

- Root and health endpoints
- Registration (including hashed passwords, duplicate usernames, invalid input) and login (wrong password, unknown user)
- All product endpoints returning `401` without a valid token
- Product create, get, list, replace, partial update and delete
- `404` for missing products and `422` for invalid data or invalid IDs
- Data isolation: one user cannot see, change or delete another user's products
- Delete-all affecting only the current user's products

## Security

What is implemented:

- Passwords are hashed with Argon2 (salted) and never stored or returned in plain text
- JWT access tokens are signed and expire (30 minutes by default)
- All product endpoints require authentication
- Product ownership comes from the token, never from client input, and is enforced on every operation
- Input is validated with Pydantic (types, lengths, ranges)
- Unexpected server errors return a generic JSON `500` message; details are only logged, not sent to the client

This is a learning project, not a production-hardened system. For example, there is no rate limiting on login.

## Error Handling

All errors are returned as JSON.

| Status | When | Example body |
|--------|------|--------------|
| `401 Unauthorized` | Missing/invalid/expired token, or wrong login credentials | `{"detail": "Not authenticated"}` |
| `404 Not Found` | Product does not exist or belongs to another user | `{"detail": "Product with id 99 not found"}` |
| `409 Conflict` | Username already taken on registration | `{"detail": "Username already taken"}` |
| `422 Unprocessable Entity` | Invalid request data or path ID | `{"detail": [{"loc": ["body", "price"], "msg": "Input should be greater than or equal to 0", ...}]}` |
| `500 Internal Server Error` | Unexpected server error | `{"detail": "Internal server error"}` |

## Example User Flow

```
Register  →  Login  →  Receive JWT  →  Authorize
    →  Create product  →  View own products  →  Update / Delete product
```

1. `POST /auth/register` with a username and password
2. `POST /auth/login` and copy the `access_token`
3. Send `Authorization: Bearer <token>` (or use **Authorize** in Swagger)
4. `POST /products` to create products
5. `GET /products` to see only your own
6. `PATCH /products/{id}` to update, `DELETE /products/{id}` or `DELETE /products` to remove

## Data Storage

Users and products are stored **in memory** (Python dictionaries in the service files). All data is lost when the
application restarts, and the app is intended to run as a single process.

## Future Improvements

These are ideas and are **not** implemented yet:

- Persistent database (PostgreSQL) with SQLAlchemy and Alembic migrations
- Pagination, search and filtering for the product list
- Docker setup
- CI pipeline to run the tests automatically
- Login rate limiting and refresh tokens

## License

No license has been specified for this project.
