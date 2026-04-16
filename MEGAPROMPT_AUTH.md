# MASTER PROMPT: Authentication + Role System (Multi-Agent Phase 1)

## CRITICAL RULES
1. ADDITIVE only. Do NOT rewrite existing files.
2. FIRST run: `git add -A && git commit -m "checkpoint before auth"` as safety checkpoint.
3. Do NOT push to git.
4. Do NOT touch persona builder, voice builder, catalog, channel webhooks, or analytics.

## WHAT THIS DOES

Adds user authentication (register/login) and role-based access to the platform.

3 roles:
- **Admin**: full access to everything — personas, catalogs, settings, analytics, all conversations, user management
- **Supervisor**: can view all conversations, customers, analytics. Cannot edit personas, settings, or manage users
- **Agent**: can only see conversations assigned to them. Cannot see analytics, settings, or user management

Login flow: email + password → JWT token → stored in localStorage → sent with every API request.

## BACKEND — NEW FILES

### Add to requirements.txt:
```
pyjwt==2.9.0
bcrypt==4.2.0
```

### New file: `backend/app/models/user.py`

```python
"""User model with role-based access."""

from sqlalchemy import Column, String, DateTime, Boolean
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, default="")
    role = Column(String, default="agent")  # "admin", "supervisor", "agent"
    is_active = Column(Boolean, default=True)
    avatar_url = Column(String, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
```

Register in `app/models/__init__.py`:
```python
from app.models.user import User  # noqa
```

### New file: `backend/app/services/auth.py`

```python
"""Authentication service — password hashing, JWT tokens, user validation."""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "change-this-to-a-random-secret-key-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Returns {"sub": user_id, "email": ..., "role": ...} or raises."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
```

### New file: `backend/app/services/auth_deps.py`

```python
"""FastAPI dependency for authentication — extracts current user from JWT."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User
from app.services.auth import decode_token


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Extract and validate JWT from Authorization header."""
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.replace("Bearer ", "")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_supervisor_or_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "supervisor"):
        raise HTTPException(status_code=403, detail="Supervisor or admin access required")
    return user
```

### New file: `backend/app/api/auth.py`

```python
"""Authentication API — register, login, user management."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User
from app.services.auth import hash_password, verify_password, create_token
from app.services.auth_deps import get_current_user, require_admin

router = APIRouter()


@router.post("/auth/register")
async def register(body: dict, db: AsyncSession = Depends(get_db)):
    """Register a new user. First user becomes admin automatically."""
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")
    display_name = body.get("display_name", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # First user = admin
    count_result = await db.execute(select(User))
    all_users = count_result.scalars().all()
    role = "admin" if len(all_users) == 0 else body.get("role", "agent")

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name or email.split("@")[0],
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_token(user.id, user.email, user.role)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
        },
    }


@router.post("/auth/login")
async def login(body: dict, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    user.last_login_at = datetime.utcnow()
    await db.commit()

    token = create_token(user.id, user.email, user.role)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
        },
    }


@router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current logged-in user."""
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


@router.get("/auth/users")
async def list_users(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """List all users. Admin only."""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        }
        for u in users
    ]


@router.patch("/auth/users/{user_id}")
async def update_user(user_id: str, body: dict, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """Update a user's role or status. Admin only."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)

    if "role" in body and body["role"] in ("admin", "supervisor", "agent"):
        user.role = body["role"]
    if "is_active" in body:
        user.is_active = body["is_active"]
    if "display_name" in body:
        user.display_name = body["display_name"]

    user.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "updated"}


@router.delete("/auth/users/{user_id}")
async def delete_user(user_id: str, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """Delete a user. Admin only. Cannot delete yourself."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)
    await db.delete(user)
    await db.commit()
    return {"status": "deleted"}
```

### Edit: `backend/app/main.py`

Add import:
```python
from app.api.auth import router as auth_router
```

Add include_router:
```python
app.include_router(auth_router, prefix="/api/v1", tags=["Auth"])
```

### Edit: `backend/.env`

Add:
```
JWT_SECRET=change-this-to-a-long-random-string-abc123xyz789
```

## FRONTEND — AUTH SYSTEM

### New file: `frontend/src/lib/auth.js`

```javascript
const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

export function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isLoggedIn() {
  return !!getToken();
}

export function getUserRole() {
  const user = getUser();
  return user?.role || 'agent';
}

export function isAdmin() {
  return getUserRole() === 'admin';
}

export function isSupervisorOrAdmin() {
  return ['admin', 'supervisor'].includes(getUserRole());
}

// Wrapper for fetch that adds Authorization header
export async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const resp = await fetch(url, { ...options, headers });
  if (resp.status === 401) {
    clearAuth();
    window.location.href = '/login';
  }
  return resp;
}
```

### New file: `frontend/src/pages/LoginPage.jsx`

```jsx
import { useState } from 'react';
import { setAuth } from '../lib/auth';

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const endpoint = isRegister ? '/api/v1/auth/register' : '/api/v1/auth/login';
    const body = { email, password };
    if (isRegister) body.display_name = displayName;

    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await resp.json();

      if (!resp.ok) {
        setError(data.detail || 'Something went wrong');
        setLoading(false);
        return;
      }

      setAuth(data.token, data.user);
      window.location.href = '/';
    } catch (e) {
      setError('Connection error');
    }
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#f9fafb', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    }}>
      <div style={{
        width: '400px', background: '#fff', borderRadius: '1rem',
        border: '1px solid #e5e7eb', padding: '2.5rem',
      }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.25rem', textAlign: 'center' }}>
          Persona Builder
        </h1>
        <p style={{ color: '#6b7280', fontSize: '0.875rem', textAlign: 'center', marginBottom: '2rem' }}>
          {isRegister ? 'Create your account' : 'Sign in to your account'}
        </p>

        {error && (
          <div style={{
            background: '#fef2f2', color: '#dc2626', padding: '0.75rem',
            borderRadius: '0.5rem', fontSize: '0.875rem', marginBottom: '1rem',
          }}>{error}</div>
        )}

        <form onSubmit={handleSubmit}>
          {isRegister && (
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ fontSize: '0.8rem', color: '#374151', display: 'block', marginBottom: '4px' }}>Name</label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Your name"
                style={{
                  width: '100%', padding: '10px 14px', border: '1px solid #e5e7eb',
                  borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
          )}

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ fontSize: '0.8rem', color: '#374151', display: 'block', marginBottom: '4px' }}>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              style={{
                width: '100%', padding: '10px 14px', border: '1px solid #e5e7eb',
                borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ fontSize: '0.8rem', color: '#374151', display: 'block', marginBottom: '4px' }}>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min 6 characters"
              required
              minLength={6}
              style={{
                width: '100%', padding: '10px 14px', border: '1px solid #e5e7eb',
                borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '12px', background: '#000', color: '#fff',
              border: 'none', borderRadius: '0.5rem', fontSize: '0.95rem',
              fontWeight: 600, cursor: loading ? 'wait' : 'pointer',
              opacity: loading ? 0.5 : 1,
            }}
          >
            {loading ? '...' : isRegister ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
          <button
            onClick={() => { setIsRegister(!isRegister); setError(''); }}
            style={{
              background: 'none', border: 'none', color: '#3b82f6',
              fontSize: '0.875rem', cursor: 'pointer',
            }}
          >
            {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Register"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

### New file: `frontend/src/pages/UsersPage.jsx`

```jsx
import { useState, useEffect } from 'react';
import { authFetch, isAdmin } from '../lib/auth';

const ROLE_COLORS = {
  admin: { bg: '#fef2f2', color: '#dc2626' },
  supervisor: { bg: '#eff6ff', color: '#2563eb' },
  agent: { bg: '#f0fdf4', color: '#16a34a' },
};

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [showInvite, setShowInvite] = useState(false);
  const [form, setForm] = useState({ email: '', password: '', display_name: '', role: 'agent' });
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const resp = await authFetch('/api/v1/auth/users');
      if (resp.ok) setUsers(await resp.json());
    } catch (e) { console.error(e); }
  };

  useEffect(() => { load(); }, []);

  const invite = async () => {
    setError('');
    const resp = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    if (!resp.ok) {
      const data = await resp.json();
      setError(data.detail || 'Error');
      return;
    }
    setShowInvite(false);
    setForm({ email: '', password: '', display_name: '', role: 'agent' });
    load();
  };

  const updateRole = async (userId, role) => {
    await authFetch(`/api/v1/auth/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    });
    load();
  };

  const toggleActive = async (userId, isActive) => {
    await authFetch(`/api/v1/auth/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: !isActive }),
    });
    load();
  };

  const deleteUser = async (userId) => {
    if (!confirm('Delete this user?')) return;
    await authFetch(`/api/v1/auth/users/${userId}`, { method: 'DELETE' });
    load();
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Team</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Manage users and roles</p>
        </div>
        <button
          onClick={() => setShowInvite(true)}
          style={{ padding: '0.5rem 1rem', background: '#000', color: '#fff', border: 'none', borderRadius: '0.5rem', fontSize: '0.875rem', cursor: 'pointer' }}
        >+ Add User</button>
      </div>

      {users.map((u) => (
        <div key={u.id} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem',
          marginBottom: '0.5rem', background: '#fff', opacity: u.is_active ? 1 : 0.5,
        }}>
          <div>
            <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>{u.display_name}</div>
            <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>{u.email}</div>
            <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: '2px' }}>
              Last login: {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'Never'}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <select
              value={u.role}
              onChange={(e) => updateRole(u.id, e.target.value)}
              style={{
                padding: '4px 10px', fontSize: '0.75rem', borderRadius: '9999px',
                border: '1px solid #e5e7eb', outline: 'none',
                background: ROLE_COLORS[u.role]?.bg || '#f3f4f6',
                color: ROLE_COLORS[u.role]?.color || '#374151',
                fontWeight: 600,
              }}
            >
              <option value="admin">Admin</option>
              <option value="supervisor">Supervisor</option>
              <option value="agent">Agent</option>
            </select>
            <button
              onClick={() => toggleActive(u.id, u.is_active)}
              style={{
                padding: '4px 10px', fontSize: '0.7rem', borderRadius: '9999px',
                background: u.is_active ? '#f0fdf4' : '#fef2f2',
                color: u.is_active ? '#16a34a' : '#dc2626',
                border: '1px solid #e5e7eb', cursor: 'pointer',
              }}
            >{u.is_active ? 'Active' : 'Inactive'}</button>
            <button
              onClick={() => deleteUser(u.id)}
              style={{ padding: '4px 10px', fontSize: '0.7rem', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer' }}
            >Delete</button>
          </div>
        </div>
      ))}

      {showInvite && (
        <div style={{ marginTop: '1rem', padding: '1.5rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem', background: '#f9fafb' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>Add New User</h3>
          {error && <div style={{ color: '#dc2626', fontSize: '0.8rem', marginBottom: '0.5rem' }}>{error}</div>}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <input type="text" placeholder="Name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }} />
            <input type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
              style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }} />
            <input type="password" placeholder="Password (min 6)" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
              style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }} />
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}
              style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }}>
              <option value="agent">Agent</option>
              <option value="supervisor">Supervisor</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button onClick={invite} disabled={!form.email || !form.password}
              style={{ padding: '8px 20px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer', opacity: (!form.email || !form.password) ? 0.4 : 1 }}>
              Create User</button>
            <button onClick={() => { setShowInvite(false); setError(''); }}
              style={{ padding: '8px 20px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
```

### Edit: `frontend/src/App.jsx`

This is the biggest frontend change — add auth guard, login route, and role-based nav.

Add imports at top:
```jsx
import LoginPage from './pages/LoginPage';
import UsersPage from './pages/UsersPage';
import { isLoggedIn, getUser, clearAuth, isAdmin } from './lib/auth';
```

Wrap the main app content with an auth check. Find the main return/render. The logic should be:

```jsx
// If not logged in and not on login page, show login
if (!isLoggedIn() && window.location.pathname !== '/login') {
  window.location.href = '/login';
  return null;
}
```

Add the login route OUTSIDE the auth-protected layout:
```jsx
<Route path="/login" element={<LoginPage />} />
```

Add the users route (admin only):
```jsx
<Route path="/users" element={<UsersPage />} />
```

In the navbar, add:
- "Team" link (only visible to admin): `{isAdmin() && <Link to="/users">Team</Link>}`
- User display + logout button at the right side of navbar:
```jsx
<div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
  <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
    {getUser()?.display_name} ({getUser()?.role})
  </span>
  <button
    onClick={() => { clearAuth(); window.location.href = '/login'; }}
    style={{ padding: '4px 12px', fontSize: '0.75rem', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer' }}
  >Logout</button>
</div>
```

IMPORTANT: Do NOT restructure the entire App.jsx. Only add the auth check at the top, the new routes, the nav link, and the user/logout display. Keep everything else exactly as is.

### Edit: `frontend/src/lib/i18n.js`

Add keys:

English:
```javascript
auth_sign_in: "Sign In",
auth_register: "Create Account",
auth_email: "Email",
auth_password: "Password",
auth_name: "Name",
auth_already_have: "Already have an account? Sign in",
auth_no_account: "Don't have an account? Register",
auth_logout: "Logout",
nav_team: "Team",
team_title: "Team",
team_subtitle: "Manage users and roles",
team_add: "+ Add User",
team_create: "Create User",
team_last_login: "Last login",
team_never: "Never",
team_active: "Active",
team_inactive: "Inactive",
```

Turkish:
```javascript
auth_sign_in: "Giriş Yap",
auth_register: "Hesap Oluştur",
auth_email: "E-posta",
auth_password: "Şifre",
auth_name: "İsim",
auth_already_have: "Zaten hesabın var mı? Giriş yap",
auth_no_account: "Hesabın yok mu? Kayıt ol",
auth_logout: "Çıkış",
nav_team: "Ekip",
team_title: "Ekip",
team_subtitle: "Kullanıcıları ve rolleri yönet",
team_add: "+ Kullanıcı Ekle",
team_create: "Kullanıcı Oluştur",
team_last_login: "Son giriş",
team_never: "Hiç",
team_active: "Aktif",
team_inactive: "Pasif",
```

## IMPORTANT NOTES

1. First user to register becomes Admin automatically — no seed needed.
2. Auth is NOT enforced on webhook endpoints (Instagram, Messenger, LiveChat) — those must remain public for Meta to send webhooks.
3. Auth is NOT enforced on the widget/chat.js endpoint — that must remain public for the livechat widget.
4. For now, auth is enforced only on the FRONTEND (redirect to login if no token). Backend endpoints remain open. In Phase 2 we will add Depends(get_current_user) to protected endpoints gradually — NOT now, to avoid breaking existing functionality.
5. Delete the .db file after applying changes — new User table needs to be created.

## TEST PLAN

1. Checkpoint: `git add -A && git commit -m "checkpoint before auth"`
2. Apply changes. `pip install pyjwt bcrypt`. Delete .db. Restart backend.
3. Open frontend → should redirect to /login.
4. Click "Register" → create account with your email → becomes Admin automatically.
5. After login → see all pages as before + "Team" link in navbar + "Logout" button.
6. Go to /users → see yourself as Admin → add a new user as "Agent".
7. Logout → login as the Agent → should see the platform (restricted features come in Phase 2).
8. Instagram/Messenger webhooks still work (test with a DM).

## SUMMARY

NEW:
- backend/app/models/user.py
- backend/app/services/auth.py
- backend/app/services/auth_deps.py
- backend/app/api/auth.py
- frontend/src/lib/auth.js
- frontend/src/pages/LoginPage.jsx
- frontend/src/pages/UsersPage.jsx

EDITED:
- backend/app/models/__init__.py (1 import)
- backend/app/main.py (2 lines)
- backend/.env (1 line)
- backend/requirements.txt (2 packages)
- frontend/src/App.jsx (imports + auth check + routes + nav items)
- frontend/src/lib/i18n.js (new keys)

## DO NOT
- ❌ DO NOT add Depends(get_current_user) to existing endpoints yet — Phase 2
- ❌ DO NOT rewrite App.jsx completely — only add the specific pieces
- ❌ DO NOT touch webhook endpoints
- ❌ DO NOT push to git

## START NOW. Checkpoint first. Delete .db after changes. Re-upload catalog + re-create persona after restart.
