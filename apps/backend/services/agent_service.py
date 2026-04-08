"""
Agent Service - Handles business logic for agent operations
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Agent
from schemas import AgentCreate, AgentUpdate
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AgentService:
    """Service layer for agent operations"""

    @staticmethod
    def create_agent(
        db: Session,
        agent_data: AgentCreate,
        owner_id: int,
        encrypted_config: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """
        Create a new agent

        Args:
            db: Database session
            agent_data: Agent creation data
            owner_id: ID of the user creating the agent
            encrypted_config: Optional encrypted config data

        Returns:
            Created Agent instance
        """
        logger.info(f"Creating agent '{agent_data.name}' for user {owner_id}")

        db_agent = Agent(
            name=agent_data.name,
            description=agent_data.description,
            config=encrypted_config,
            owner_id=owner_id,
            is_published=agent_data.is_published,
            tags=agent_data.tags,
            category=agent_data.category,
            version=agent_data.version,
            role=agent_data.role,
            skills=agent_data.skills,
            ai_provider=agent_data.ai_provider,
            model_name=agent_data.model_name,
            temperature=agent_data.temperature
        )

        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)

        logger.info(f"Agent created successfully with ID {db_agent.id}")
        return db_agent

    @staticmethod
    def get_agent_by_id(db: Session, agent_id: int) -> Optional[Agent]:
        """
        Get an agent by ID

        Args:
            db: Database session
            agent_id: ID of the agent to retrieve

        Returns:
            Agent instance if found, None otherwise
        """
        return db.query(Agent).filter(Agent.id == agent_id).first()

    @staticmethod
    def get_all_agents(
        db: Session,
        owner_id: Optional[int] = None,
        include_system: bool = True
    ) -> List[Agent]:
        """
        Get all agents, optionally filtered by owner

        Args:
            db: Database session
            owner_id: Optional owner ID to filter by
            include_system: Whether to include system agents (owner_id is NULL)

        Returns:
            List of Agent instances
        """
        query = db.query(Agent)

        if owner_id:
            if include_system:
                query = query.filter(
                    (Agent.owner_id == owner_id) | (Agent.owner_id.is_(None))
                )
            else:
                query = query.filter(Agent.owner_id == owner_id)
        elif not include_system:
            query = query.filter(Agent.owner_id.isnot(None))

        return query.all()

    @staticmethod
    def update_agent(
        db: Session,
        agent: Agent,
        agent_data: AgentUpdate,
        encrypted_config: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """
        Update an existing agent

        Args:
            db: Database session
            agent: Agent instance to update
            agent_data: Update data
            encrypted_config: Optional encrypted config data

        Returns:
            Updated Agent instance
        """
        logger.info(f"Updating agent {agent.id}")

        # Update fields if provided
        if agent_data.name is not None:
            agent.name = agent_data.name
        if agent_data.description is not None:
            agent.description = agent_data.description
        if encrypted_config is not None:
            agent.config = encrypted_config
        if agent_data.is_published is not None:
            agent.is_published = agent_data.is_published
        if agent_data.tags is not None:
            agent.tags = agent_data.tags
        if agent_data.category is not None:
            agent.category = agent_data.category
        if agent_data.version is not None:
            agent.version = agent_data.version
        if agent_data.role is not None:
            agent.role = agent_data.role
        if agent_data.skills is not None:
            agent.skills = agent_data.skills
        if agent_data.ai_provider is not None:
            agent.ai_provider = agent_data.ai_provider
        if agent_data.model_name is not None:
            agent.model_name = agent_data.model_name
        if agent_data.temperature is not None:
            agent.temperature = agent_data.temperature

        # Update timestamp
        agent.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(agent)

        logger.info(f"Agent {agent.id} updated successfully")
        return agent

    @staticmethod
    def delete_agent(db: Session, agent: Agent) -> bool:
        """
        Delete an agent

        Args:
            db: Database session
            agent: Agent instance to delete

        Returns:
            True if successful
        """
        logger.info(f"Deleting agent {agent.id}")

        db.delete(agent)
        db.commit()

        logger.info(f"Agent {agent.id} deleted successfully")
        return True

    @staticmethod
    def get_agents_by_role(
        db: Session,
        role: str,
        owner_id: Optional[int] = None
    ) -> List[Agent]:
        """
        Get agents by role

        Args:
            db: Database session
            role: Role to filter by
            owner_id: Optional owner ID to filter by

        Returns:
            List of Agent instances matching the role
        """
        query = db.query(Agent).filter(Agent.role == role)

        if owner_id:
            query = query.filter(
                (Agent.owner_id == owner_id) | (Agent.owner_id.is_(None))
            )

        return query.all()

    @staticmethod
    def get_agents_by_skills(
        db: Session,
        skills: List[str],
        owner_id: Optional[int] = None
    ) -> List[Agent]:
        """
        Get agents that have any of the specified skills

        Args:
            db: Database session
            skills: List of skills to filter by
            owner_id: Optional owner ID to filter by

        Returns:
            List of Agent instances matching the skills
        """
        # This is a simple implementation - in production you might want
        # to use JSON operators for better performance
        agents = db.query(Agent)

        if owner_id:
            agents = agents.filter(
                (Agent.owner_id == owner_id) | (Agent.owner_id.is_(None))
            )

        # Filter by skills (client-side filtering for simplicity)
        # In production, use database JSON operators
        filtered_agents = []
        for agent in agents.all():
            if agent.skills:
                agent_skills = agent.skills if isinstance(agent.skills, list) else []
                if any(skill.lower() in [s.lower() for s in agent_skills] for skill in skills):
                    filtered_agents.append(agent)

        return filtered_agents
