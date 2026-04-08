from collections import defaultdict
from typing import Dict, List, Tuple

from utils.config import MAX_HISTORY_MESSAGES

# In-memory history for demo/development.
_history_store: Dict[str, List[Tuple[str, str]]] = defaultdict(list)


def get_history(session_id: str) -> List[Tuple[str, str]]:
    return _history_store[session_id][-MAX_HISTORY_MESSAGES:]


def append_history(session_id: str, question: str, answer: str) -> None:
    _history_store[session_id].append((question, answer))
