from dataclasses import asdict, dataclass


@dataclass
class AgentInteraction:
    """Data class for tracking agent interactions."""
    agent_name: str
    action: str
    prompt: str
    response: str
    timestamp: float
    processing_time: float
    token_count_estimate: int

    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)