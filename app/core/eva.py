from langgraph.graph import StateGraph, END, START
from dotenv import load_dotenv

from core.classes import EvaState
from core.nodes import (
    eva_initialize, 
    eva_end, 
    eva_converse, 
    eva_sense, 
    eva_action,
    router_sense, 
    router_action, 
    router_action_results,
    router_initialize,
)

from core.nodes_setup import (
    eva_setup,
    router_setup
)

load_dotenv()

class EVA:
    """
    Class to construct the assistant.
    nodes:
        - initialize: Initialize the assistant.
        - sense: Let EVA sense the environment.
        - converse: Main execution node.
        - action: Use tools to perform actions.
        - end: End the session.
    """
    
    def __init__(self) -> None:
        self.workflow = self._initialize_graph()
        self.app = self.workflow.compile()
        self.app.invoke({"status": "initialize"}, {"recursion_limit": 100000})

    def _initialize_graph(self)-> StateGraph:
        """ Initialize the graph """
        
        workflow = StateGraph(EvaState)
        workflow.add_node("node_initialize", eva_initialize)
        workflow.add_node("node_sense", eva_sense)
        workflow.add_node("node_converse", eva_converse)
        workflow.add_node("node_action", eva_action)
        workflow.add_node("node_end", eva_end)
        
        workflow.add_edge(START, "node_initialize")
        workflow.add_conditional_edges("node_initialize", router_initialize)
        workflow.add_conditional_edges("node_converse", router_action)
        workflow.add_conditional_edges("node_action", router_action_results)
        workflow.add_conditional_edges("node_sense", router_sense)
        
        # Setup nodes
        workflow.add_node("node_setup", eva_setup)
        workflow.add_conditional_edges("node_setup", router_setup)
        
        # End Node
        workflow.add_edge("node_end", END)
        
        return workflow

