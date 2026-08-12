"""
Base Agent Abstract Class.
Defines the standard interface for all specialized agents in the system.
"""

import time
from abc import ABC, abstractmethod
from typing import Any

from utils.logger import logger


class BaseAgent(ABC):
    """
    Abstract base class for all AI Risk Guard agents.
    """
    
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the agent's core responsibility.
        
        Args:
            context: Shared state/memory containing data from previous agents.
            
        Returns:
            Updated context or specific result from this agent.
        """

    def execute_with_metrics(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute agent with metrics collection.
        
        Args:
            context: Shared state/memory containing data from previous agents.
            
        Returns:
            Updated context or specific result from this agent.
        """
        start_time = time.time()
        context.get("trace_id")
        
        try:
            result = self.execute(context)
            duration = time.time() - start_time
            
            # Log timing
            self.log(f"{self.name} completed in {duration:.3f}s", "debug")
            
            # Update metrics if available
            try:
                from app.metrics import agent_duration
                agent_duration.labels(agent=self.name.lower()).observe(duration)
            except ImportError:
                pass
                
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log error with timing
            self.log(f"{self.name} failed after {duration:.3f}s: {e}", "error")
            
            # Update error metrics if available
            try:
                from app.metrics import agent_errors
                agent_errors.labels(
                    agent=self.name.lower(),
                    error_type=type(e).__name__
                ).inc()
            except ImportError:
                pass
                
            raise

    def log(self, message: str, level: str = "info"):
        """Standardized logging for agents."""
        LEVEL_MAP = {
            "error": logger.error,
            "warning": logger.warning,
            "warn": logger.warning,
            "debug": logger.debug,
            "info": logger.info,
        }
        fn = LEVEL_MAP.get(level, logger.info)
        fn(message, self.name.upper())
