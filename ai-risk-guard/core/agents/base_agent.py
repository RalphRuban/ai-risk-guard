"""
Base Agent Abstract Class.
Defines the standard interface for all specialized agents in the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from utils.logger import logger

class BaseAgent(ABC):
    """
    Abstract base class for all AI Risk Guard agents.
    """
    
    def __init__(self, name: str):
        self.name = name
        # Individual agent logs removed for cleaner startup experience.

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's core responsibility.
        
        Args:
            context: Shared state/memory containing data from previous agents.
            
        Returns:
            Updated context or specific result from this agent.
        """
        pass

    def log(self, message: str, level: str = "info"):
        """Standardized logging for agents."""
        if level == "error":
            logger.error(message, self.name.upper())
        elif level == "debug":
            logger.debug(message, self.name.upper())
        else:
            logger.info(message, self.name.upper())
