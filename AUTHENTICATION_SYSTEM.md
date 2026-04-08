
# Authentication System Documentation

## Overview
The Flowora backend has a complete, production-ready authentication system implemented using FastAPI, SQLAlchemy, JWT tokens, and bcrypt for password hashing.

## Components Implemented

### 1. User Database Model (`models/user.py`)
```python
class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    role = Column(String, default="user")  # user, admin, developer
    is_active = Column(String, default=True)
    referral_code = Column(String, unique=True, index=True, nullable=True)
    executions_this_month = Column(Integer, default=0)
    tokens_used_this_month = Column(Integer, default=0)
    subscription_tier = Column(String, default="free")
    subscription_status = Column(String, default="active")
    is_email_verified = Column(String, default=False)
    email_verification_code = Column(String, nullable=True)
    email_verification_expires_at = Column(DateTime, nullable=True)
    password_reset_token = Column(String, nullable=True)
    password_reset_expires_at = Column(DateTime, nullable=True)
```

### 2. Security Module (`security.py`)
- **Password Hashing**: Uses bcrypt with passlib
- **JWT Tokens**: Implements access and refresh tokens
- **Token Creation**: 
  - `create_access_token()` - Creates short-lived access tokens
  - `create_refresh_token()` - Creates long-lived refresh tokens (30 days)
- **Token Verification**:
  - `get_current_user()` - Validates JWT and returns current user
  - `get_current_active_user()` - Ensures user is active
  - `RoleChecker` - Role-based access control

### 3. Authentication Schemas (`schemas.py`)
```python
class UserCreate(BaseModel):
    email: str
    password: str
    referral_code: Optional[str] = None
    subscription_tier: Optional[str] = "free"
    subscription_status: Optional[str] = "active"

class User(BaseModel):
    id: int
    email: str
    created_at: datetime
    referral_code: Optional[str] = None
    executions_this_month: int = 0
    tokens_used_this_month: int = 0
    subscription_tier: str = "free"
    subscription_status: str = "active"
    is_email_verified: bool = False

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    role: Optional[str] = "user"
```

### 4. Auth Router (`routers/auth.py`)
Endpoints implemented:

#### POST /auth/register
- Creates new user account
- Hashes password with bcrypt
- Generates unique referral code
- Sends email verification code
- Handles referral system

#### POST /auth/login
- Authenticates user credentials
- Returns JWT access token (15 min expiry)
- Returns refresh token (30 days expiry)
- Stores refresh token in database

#### POST /auth/refresh
- Validates refresh token
- Issues new access token
- Checks token revocation status

#### POST /auth/logout
- Revokes refresh token
- Requires authentication

#### GET /auth/me
- Returns current user profile
- Requires authentication
- Protected endpoint

#### POST /auth/verify-email
- Verifies email with 6-digit code
- Requires authentication
- Marks user as verified

#### POST /auth/resend-verification-code
- Resends verification code
- Requires authentication

#### POST /auth/forgot-password
- Initiates password reset
- Sends reset link to email
- Security: Doesn't reveal if email exists

#### POST /auth/reset-password
- Resets password using token
- Validates token and expiry
- Hashes new password

### 5. Protected Endpoints
All agent endpoints are protected with authentication:

```python
@router.post("/", response_model=AgentSchema)
def create_agent(agent: AgentCreate, request: Request, db: Session = Depends(get_db), 
                 current_user: User = Depends(get_current_user)):
    # Only authenticated users can create agents
    ...

@router.get("/", response_model=List[AgentSchema])
def list_agents(db: Session = Depends(get_db), 
                current_user: User = Depends(get_current_user)):
    # Only authenticated users can list agents
    ...
```

## How to Use

### 1. Register a New User
```bash
POST /auth/register
{
  "email": "user@example.com",
  "password": "securepassword123",
  "referral_code": "ABC12345"  # Optional
}
```

Response:
```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-03-11T00:00:00",
  "is_email_verified": false,
  "subscription_tier": "free",
  "subscription_status": "active"
}
```

### 2. Login
```bash
POST /auth/login
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "user"
}
```

### 3. Access Protected Endpoints
Include the access token in the Authorization header:
```bash
GET /agents
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 4. Get Current User Profile
```bash
GET /auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Response:
```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-03-11T00:00:00",
  "is_email_verified": true,
  "subscription_tier": "free",
  "subscription_status": "active"
}
```

### 5. Refresh Access Token
```bash
POST /auth/refresh
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "user"
}
```

## Security Features

1. **Password Security**
   - Never stored as plain text
   - Hashed with bcrypt
   - Salted automatically

2. **JWT Tokens**
   - Access tokens expire in 15 minutes
   - Refresh tokens expire in 30 days
   - Tokens include user ID and role
   - Signed with secret key

3. **Email Verification**
   - 6-digit verification codes
   - Codes expire in 15 minutes
   - Required before agent execution

4. **Password Reset**
   - Secure token-based reset
   - Tokens expire in 30 minutes
   - Tokens are hashed in database

5. **Role-Based Access Control**
   - User roles: user, admin, developer
   - RoleChecker dependency for protected routes
   - Admin privileges for system operations

6. **Refresh Token Management**
   - Stored in database
   - Can be revoked (logout)
   - Tracked for security

## Testing in Swagger UI

1. Navigate to `http://localhost:8000/docs`
2. Click on `/auth/register`
3. Click "Try it out"
4. Enter email and password
5. Click "Execute"
6. Copy the access token from response
7. Click "Authorize" button (top right)
8. Enter: `Bearer <your_access_token>`
9. Click "Authorize"
10. Now all protected endpoints are accessible

## Configuration

Authentication settings are in `config.py`:
```python
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
```

## Dependencies

Required packages:
- fastapi
- sqlalchemy
- pydantic
- python-jose[cryptography]
- passlib[bcrypt]
- python-multipart

## Notes

- All passwords are hashed with bcrypt before storage
- JWT tokens are signed with HS256 algorithm
- Access tokens are short-lived for security
- Refresh tokens allow seamless re-authentication
- Email verification is required for agent execution
- Password reset flow is secure and time-limited
- Role-based access control is implemented
- All sensitive operations require authentication
- Audit logging tracks user actions
