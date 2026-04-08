from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str
    referral_code: Optional[str] = None
    subscription_tier: Optional[str] = "free"
    subscription_status: Optional[str] = "active"

class User(UserBase):
    id: int
    created_at: datetime
    referral_code: Optional[str] = None # Their own code
    executions_this_month: int = 0
    tokens_used_this_month: int = 0
    subscription_tier: str = "free"
    subscription_status: str = "active"
    is_email_verified: bool = False
    organization_id: Optional[int] = None
    class Config:
        from_attributes = True


class VerifyEmailRequest(BaseModel):
    code: str  # verification token or legacy code


class ResendVerificationRequest(BaseModel):
    email: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UserDashboard(BaseModel):
    """User dashboard stats and profile"""
    id: int
    email: str
    subscription_tier: str
    subscription_status: str
    executions_this_month: int
    tokens_used_this_month: int
    is_email_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Referral(BaseModel):
    id: int
    code: str
    status: str
    reward_claimed: bool
    reward_points: Optional[int] = 0
    created_at: datetime
    
    class Config:
        from_attributes = True

class AnnouncementCreate(BaseModel):
    title: str
    content: str
    type: str = "feature"

class Announcement(AnnouncementCreate):
    id: int
    created_at: datetime
    is_active: bool = True
    
    class Config:
        from_attributes = True

class CommunityPostCreate(BaseModel):
    content: str
    agent_id: Optional[int] = None
    parent_id: Optional[int] = None
    type: str = "comment"

class CommunityPost(CommunityPostCreate):
    id: int
    user_id: int
    likes: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class OrganizationBase(BaseModel):
    name: str

class Organization(OrganizationBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class UserStats(BaseModel):
    total_executions: int
    total_time_saved: float
    productivity_score: float
    last_updated: datetime
    
    class Config:
        from_attributes = True

class MarketplaceListingBase(BaseModel):
    price: float
    category: Optional[str] = None
    is_active: bool = True
    listing_type: Optional[str] = "agent"
    resource_id: Optional[int] = None
    downloads: int = 0
    rating: float = 0.0
    version: Optional[str] = "1.0.0"

class MarketplaceListingCreate(MarketplaceListingBase):
    agent_id: Optional[int] = None

class MarketplaceListing(MarketplaceListingBase):
    id: int
    agent_id: int
    seller_id: Optional[int] = None
    created_at: Optional[datetime] = None
    agent: Optional["Agent"] = None
    
    class Config:
        from_attributes = True

class Purchase(BaseModel):
    id: int
    listing_id: int
    buyer_id: int
    amount: float
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class MarketplaceReviewCreate(BaseModel):
    rating: int
    comment: Optional[str] = None

class MarketplaceReview(MarketplaceReviewCreate):
    id: int
    listing_id: int
    user_id: int
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    role: Optional[str] = "user"

class TokenData(BaseModel):
    email: Optional[str] = None


class APIKeyCreate(BaseModel):
    name: Optional[str] = "default"


class APIKey(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyCreated(APIKey):
    api_key: str

class WorkflowBase(BaseModel):
    name: str
    config_json: Dict[str, Any]
    description: Optional[str] = None
    is_public: Optional[bool] = False

class WorkflowCreate(WorkflowBase):
    pass

class Workflow(WorkflowBase):
    id: int
    owner_id: Optional[int] = None
    clone_count: Optional[int] = 0
    install_count: Optional[int] = 0

    class Config:
        from_attributes = True

class AgentBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_published: bool = False
    tags: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = "1.0.0"
    role: Optional[str] = None
    skills: Optional[List[str]] = None
    ai_provider: Optional[str] = "openai"
    model_name: Optional[str] = "gpt-3.5-turbo"
    temperature: Optional[float] = 0.7

class AgentCreate(AgentBase):
    pass

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_published: Optional[bool] = None
    tags: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    role: Optional[str] = None
    skills: Optional[List[str]] = None
    ai_provider: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None

class Agent(AgentBase):
    id: int
    owner_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    ai_provider: Optional[str] = "local"
    model_name: Optional[str] = "qwen2.5:7b-instruct"
    temperature: Optional[float] = 0.7

    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

# Alias for clarity in routers
AgentSchema = Agent

class ExecutionBase(BaseModel):
    agent_id: int
    status: str
    result: str

class ExecutionCreate(ExecutionBase):
    pass

class Execution(ExecutionBase):
    id: int
    timestamp: datetime
    prompt_version_id: Optional[int] = None

    class Config:
        from_attributes = True


class AgentRunBase(BaseModel):
    agent_id: int
    input_prompt: Optional[str] = None
    output_response: str
    execution_time: int


class AgentRunCreate(AgentRunBase):
    pass


class AgentRun(AgentRunBase):
    id: int
    created_at: datetime
    prompt_version_id: Optional[int] = None

    class Config:
        from_attributes = True


class WorkflowTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    version: Optional[str] = "1.0.0"
    config_json: Optional[Dict[str, Any]] = None


class WorkflowTemplateCreate(WorkflowTemplateBase):
    pass


class WorkflowTemplate(WorkflowTemplateBase):
    id: int
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class ToolConfigTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    version: Optional[str] = "1.0.0"
    tool_config: Optional[Dict[str, Any]] = None


class ToolConfigTemplateCreate(ToolConfigTemplateBase):
    pass


class ToolConfigTemplate(ToolConfigTemplateBase):
    id: int
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True
