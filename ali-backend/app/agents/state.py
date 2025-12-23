from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared memory between the Analyst and the Strategist agents.

    This structure holds the user identifier, raw campaign metrics pulled from
    Firestore, any anomalies discovered by the Analyst, the strategy proposal
    produced by the Strategist, and the chat/message history annotated for
    LangGraph processing and debugging.
    """

    user_id: str
    campaign_data: List[Dict[str, Any]]
    anomalies: List[str]
    strategy_plan: Dict[str, Any]
    messages: Annotated[List[Any], add_messages]
