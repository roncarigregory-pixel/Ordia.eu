# Auth Testing Playbook

Step 1: MongoDB Verification
- Verify admin/user documents exist with bcrypt hashes starting with `$2b$`.
- Verify unique index on users.email.

Step 2: API Testing (Bearer token flow)
- POST /api/auth/register {company_name, name, email, password} -> returns {access_token, user}
- POST /api/auth/login {email, password} -> returns {access_token, user}
- GET /api/auth/me with header `Authorization: Bearer <token>` -> returns user
- Wrong password should fail; 5 failed attempts lock for 15 min.

Notes:
- Tokens are returned in JSON body and sent via Authorization: Bearer header (no cookies).
- Multi-tenant: every domain object is scoped by company_id.
