from dataclasses import dataclass, field
from typing import Dict, List

from .conversations import Conversation

@dataclass
class AppState:
    known_users: List[str] = field(default_factory=list)
    conversations: Dict[str,Conversation] = field(default_factory=dict)
    message_count: int = 0
    unknown_count: int = 0
    event_count: int = 0
    start_time: float = 0
    bot_user_id: str = ''
    bot_user_ref: str = ''

app_state = AppState()

