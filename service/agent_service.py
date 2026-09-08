from src.agent import compiled_agent
from src.audit import record_event


def build_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def start_agent(thread_id: str, user_message: str) -> dict:
    config = build_config(thread_id)
    current_state = compiled_agent.get_state(config)
    values = current_state.values or {}

    if current_state.next:
        record_event("request_rejected_pending_thread", thread_id)
        raise ValueError("This thread already has a pending decision.")

    initial_state = {
        "user_message": user_message,
        "intent": "",
        "customer_email": "",
        "order_id": "",
        "refund_amount": 0.0,
        "requires_approval": False,
        "status_message": "",
        "approval_decision": "",
        "approval_granted": False,
        "logs": values.get("logs", [])
        + ["Network request received by agent service."],
    }

    final_output = {}
    for output in compiled_agent.stream(
        initial_state, config, stream_mode="values"
    ):
        final_output = output

    record_event(
        "agent_request_completed",
        thread_id,
        status=final_output.get("status_message", "Processing complete."),
        order_id=final_output.get("order_id", ""),
    )

    state = compiled_agent.get_state(config)
    paused = bool(state.next and "human_approval" in state.next)

    return {
        "status": "held_for_review" if paused else "completed",
        "current_status_msg": final_output.get(
            "status_message", "Processing complete."
        ),
        "logs": final_output.get("logs", []),
    }


def decide_agent(thread_id: str, action: str) -> dict:
    action = action.upper()

    if action not in {"APPROVE", "REJECT"}:
        raise ValueError("Action must be APPROVE or REJECT.")

    config = build_config(thread_id)
    state = compiled_agent.get_state(config)

    if not state.next or "human_approval" not in state.next:
        record_event("decision_rejected_no_pending_approval", thread_id, action=action)
        raise ValueError("No pending approval exists for this thread.")

    decision = "approved" if action == "APPROVE" else "rejected"

    compiled_agent.update_state(
        config,
        {
            "approval_granted": action == "APPROVE",
            "approval_decision": decision,
            "status_message": (
                "Transaction approved by administrator."
                if action == "APPROVE"
                else "Transaction rejected by administrator."
            ),
        },
        as_node="human_approval",
    )

    final_output = {}
    for output in compiled_agent.stream(None, config, stream_mode="values"):
        final_output = output

    record_event("admin_decision_completed", thread_id, action=action)

    return {
        "status": "completed" if action == "APPROVE" else "rejected",
        "current_status_msg": final_output.get(
            "status_message",
            "Transaction decision completed.",
        ),
        "logs": final_output.get("logs", []),
    }