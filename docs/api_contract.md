# PenguWave API Contract

Base URL: `http://localhost:3001`

These are the expected endpoints. Response shapes and status codes below are **suggestions** — feel free to deviate if you have a better approach. Document your decisions.

---

## Authentication

### `POST /api/auth/login`

Authenticate a user and start a session.

- **Body:** `{ "email": "...", "password": "..." }`
- **Success (200):**
  ```json
  { "token": "...", "user": { "id": "...", "email": "...", "role": "..." } }
  ```
- **Invalid credentials (401):**
  ```json
  { "error": "Invalid email or password" }
  ```

### `POST /api/auth/logout`

End the current session.

- **Success (200):** `{ "message": "Logged out" }`

### `GET /api/auth/me`

Get the currently authenticated user's info.

- **Headers:** `Authorization: Bearer <token>`
- **Success (200):**
  ```json
  { "id": "...", "email": "...", "role": "...", "status": "..." }
  ```
- **Not authenticated (401):**
  ```json
  { "error": "Authentication required" }
  ```

---

## Events

All event endpoints require authentication.

### `GET /api/events`

Returns the list of security events.

- **Success (200):**
  ```json
  [
    {
      "id": "evt-001",
      "timestamp": "2025-02-18T14:32:01Z",
      "severity": "HIGH",
      "title": "...",
      "description": "...",
      "assetHostname": "...",
      "assetIp": "...",
      "sourceIp": "...",
      "tags": ["..."]
    }
  ]
  ```

> Pagination is not required, but consider it if you have time.

### `GET /api/events/:id`

Returns a single event by ID.

- **Success (200):** Single event object (same shape as above)
- **Not found (404):** `{ "error": "Event not found" }`

---

## Users

User management endpoints require the **admin** role. Non-admin users should receive a `403 Forbidden` response.

### `GET /api/users`

Returns the list of users. Passwords must **never** be included in the response.

- **Success (200):**
  ```json
  [
    { "id": "...", "email": "...", "role": "admin", "status": "active" }
  ]
  ```

### `POST /api/users`

Create a new user.

- **Body:** `{ "email": "...", "password": "...", "role": "..." }`
- **Success (201):** The created user (without password)
- **Validation error (400):** `{ "error": "..." }`

### `PATCH /api/users/:id`

Update a user's role or status.

- **Body:** `{ "role": "..." }` and/or `{ "status": "..." }`
- **Success (200):** The updated user
- **Not found (404):** `{ "error": "User not found" }`

### `DELETE /api/users/:id`

Delete a user.

- **Success (200):** `{ "message": "User deleted" }`
- **Not found (404):** `{ "error": "User not found" }`

---

## Error Responses

All error responses should follow a consistent format:

```json
{ "error": "Human-readable error message" }
```

Common status codes:
- `200` — Success
- `201` — Created
- `400` — Bad request / validation error
- `401` — Not authenticated
- `403` — Not authorized (wrong role)
- `404` — Resource not found
- `500` — Server error
