from typing import Dict, Any, TypedDict
from importlib import import_module

_langgraph = import_module("langgraph.graph")
StateGraph = _langgraph.StateGraph
END = _langgraph.END

MemorySaver = import_module("langgraph.checkpoint.memory").MemorySaver

ChatOllama = import_module("langchain_ollama").ChatOllama
from config.settings import settings
from src.database import MockDatabase
from src.schema import ExtractedCustomerIntent

db = MockDatabase()

# Ollama runs the model locally and does not require an API key or paid credits.
llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    temperature=0,
    base_url=settings.OLLAMA_BASE_URL,
)
structured_llm = llm.with_structured_output(ExtractedCustomerIntent)

# 1. Update State to accept raw user chat input
class AgentState(TypedDict):
    user_message: str
    intent: str
    customer_email: str
    order_id: str
    refund_amount: float
    requires_approval: bool
    approval_granted: bool
    approval_decision: str
    status_message: str
    logs: list[str]

# 2. NEW NODE: The LLM Intent and Data Extraction Engine
def intent_classifier_node(state: AgentState) -> Dict[str, Any]:
    current_logs = list(state.get("logs", []))
    current_logs.append("Executing Node: intent_classifier_node (LLM Processing)")
    current_logs.append(f"Analyzing user text: '{state['user_message']}'")
    
    # Prompting the LLM to extract targets
    system_prompt = (
        "You are an elite e-commerce support triage bot. Analyze the user message. "
        "Extract their email, order ID, and intent. If they want a refund but missed providing "
        "their email or order ID, set intent to 'missing_info' and draft a polite request."
    )
    
    # Execute LLM structured call
    extraction = structured_llm.invoke([
        ("system", system_prompt),
        ("human", state["user_message"])
    ])
    
    current_logs.append(f"LLM Extraction Complete. Detected Intent: {extraction.intent}")
    
    return {
        "customer_email": extraction.email if extraction.email else "",
        "order_id": extraction.order_id if extraction.order_id else "",
        "status_message": extraction.clarification_message if extraction.clarification_message else "Intent parsed successfully.",
        "intent": extraction.intent,
        "logs": current_logs
    }

# 3. Existing Deterministic Nodes (Modified safely for State structure)
def verify_order_node(state: AgentState) -> Dict[str, Any]:
    current_logs = list(state.get("logs", []))
    current_logs.append("Executing Node: verify_order_node")
    
    order_record = db.get_order(state["order_id"])
    if not order_record or order_record["email"] != state["customer_email"]:
        current_logs.append("Security/Verification mismatch inside database lookup.")
        return {"refund_amount": 0.00, "status_message": "Error: Order validation failed.", "logs": current_logs}
        
    return {"refund_amount": order_record["price"], "logs": current_logs}

def process_refund_policy_node(state: AgentState) -> Dict[str, Any]:
    current_logs = list(state.get("logs", []))
    current_logs.append("Executing Node: process_refund_policy_node")
    
    if state["refund_amount"] > settings.MAX_AUTO_REFUND_LIMIT:
        return {"requires_approval": True, "status_message": "Halted: Requires manager approval.", "logs": current_logs}
    return {"requires_approval": False, "status_message": "Approved automatically.", "logs": current_logs}

def execute_stripe_refund_node(state: AgentState) -> Dict[str, Any]:
    current_logs = list(state.get("logs", []))
    if not db.update_order_status(state["order_id"], "Refunded"):
        current_logs.append("Refund blocked: order is missing or already refunded.")
        return {"status_message": "Refund was already completed or is unavailable.", "logs": current_logs}

    current_logs.append("Payout engine completed ledger updates.")
    return {"status_message": f"Success: Liquid refund of ${state['refund_amount']} cleared.", "logs": current_logs}

def human_approval_node(state: AgentState) -> Dict[str, Any]:
    current_logs = list(state.get("logs", []))
    current_logs.append("Transaction paused for human approval.")

    return {
        "approval_decision": state.get("approval_decision", "pending"),
        "approval_granted": state.get("approval_granted", False),
        "status_message": "Halted: Requires manager approval.",
        "logs": current_logs,
    }


def approval_routing_edge(state: AgentState) -> str:
    if state.get("approval_decision") == "approved":
        return "execute_stripe_refund"
    return END

# 4. NEW Router Logic: Paths based on LLM Intent analysis
def classifier_routing_edge(state: AgentState) -> str:
    intent = state["intent"]
    if intent == "missing_info" or intent == "general_query":
        return END
    return "verify_order"

def financial_routing_edge(state: AgentState) -> str:
    if state["refund_amount"] == 0:
        return END
    if state["requires_approval"] and not state["approval_granted"]:
        return "human_approval"
    return "execute_stripe_refund"

# 5. Graph Re-Assembly
workflow = StateGraph(AgentState)

workflow.add_node("intent_classifier", intent_classifier_node)
workflow.add_node("verify_order", verify_order_node)
workflow.add_node("process_refund_policy", process_refund_policy_node)
workflow.add_node("human_approval", human_approval_node)
workflow.add_node("execute_stripe_refund", execute_stripe_refund_node)

# Set the LLM as the gatekeeper entry point
workflow.set_entry_point("intent_classifier")

# Route 1: From LLM classifier out to database or system exit
workflow.add_conditional_edges(
    "intent_classifier",
    classifier_routing_edge,
    {
        END: END,
        "verify_order": "verify_order"
    }
)

workflow.add_edge("verify_order", "process_refund_policy")

# Route 2: Financial risk gate
workflow.add_conditional_edges(
    "process_refund_policy",
    financial_routing_edge,
    {
        END: END,
        "human_approval": "human_approval",
        "execute_stripe_refund": "execute_stripe_refund"
    }
)

workflow.add_conditional_edges(
    "human_approval",
    approval_routing_edge,
    {
        END: END,
        "execute_stripe_refund": "execute_stripe_refund",
    },
)

# Change this initialization near the bottom of src/agent.py:
checkpointer = MemorySaver()

compiled_agent = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_approval"],
)