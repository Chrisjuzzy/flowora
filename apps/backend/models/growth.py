from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Text
from sqlalchemy.orm import relationship, backref
from datetime import datetime
from database import Base

class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("users.id"))
    referee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    referred_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    code = Column(String, unique=True, index=True)
    status = Column(String, default="pending") # pending, completed
    reward_claimed = Column(Boolean, default=False)
    reward_points = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    referrer = relationship("User", foreign_keys=[referrer_id], backref="referrals_sent")
    referee = relationship("User", foreign_keys=[referee_id], backref="referral_received")
    referred_user = relationship("User", foreign_keys=[referred_user_id], backref="referrals_received")

class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(Text)
    type = Column(String, default="feature") # feature, maintenance, news
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    content = Column(Text)
    parent_id = Column(Integer, ForeignKey("community_posts.id"), nullable=True)
    type = Column(String, default="comment") # comment, idea, question
    likes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="posts")
    agent = relationship("Agent", backref="posts")
    parent = relationship("CommunityPost", remote_side=[id], backref="replies")

class UserStats(Base):
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    total_executions = Column(Integer, default=0)
    total_time_saved = Column(Float, default=0.0) # in minutes
    productivity_score = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="stats")
