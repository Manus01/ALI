from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.nodes import analyst_node, strategist_node

# 1. Initialize the Graph with our State schema
workflow = StateGraph(AgentState)

# 2. Add Nodes (The "Brain Cells")
workflow.add_node("analyst", analyst_node)
workflow.add_node("strategist", strategist_node)

# 3. Define Edges (The Connections)
# Start -> Analyst -> Strategist -> End
workflow.set_entry_point("analyst")
workflow.add_edge("analyst", "strategist")
workflow.add_edge("strategist", END)

# 4. Compile the Graph into a runnable application
app_graph = workflow.compile()