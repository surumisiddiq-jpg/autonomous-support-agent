from pydantic import BaseModel, Field
from typing import Literal, Optional

class ExtractedCustomerIntent(BaseModel):
    intent: Literal["refund_request", "general_query", "missing_info"] = Field(
        description="The primary intent of the customer. 'missing_info' if they want a refund but forgot email or order ID."
    )
    email: Optional[str] = Field(None, description="The customer's extracted email address.")
    order_id: Optional[str] = Field(None, description="The extracted Order ID, converted strictly to uppercase (e.g., ORD-111).")
    clarification_message: Optional[str] = Field(
        None, description="If information is missing, write a polite message asking for the specific missing details."
    )
