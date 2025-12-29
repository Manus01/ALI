import logging

class BaseAgent:
    """
    Enterprise Base Agent for ALI Platform.
    Provides standardized logging and common AI utility methods.
    """
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"ali_platform.{name}")
        self.name = name

    def log_task(self, message: str):
        self.logger.info(f"[{self.name}] {message}")

    def handle_error(self, error: Exception):
        self.logger.error(f"[{self.name}] Critical Error: {str(error)}")
        # You can add global error reporting logic here later (e.g., Sentry)
        raise error