from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

#TODO: DEAL WITH WEBHOOK EXTRA DATA
class Fields(str, Enum):
    account_alerts = "account_alerts"
    account_review_update = "account_review_update"
    account_update = "account_update"
    automatic_events = "automatic_events"
    business_capability_update = "business_capability_update"
    history = "history"
    message_template_components_update = "message_template_components_update"
    message_template_quality_update = "message_template_quality_update"
    message_template_status_update = "message_template_status_update"
    messages = "messages"
    partner_solutions = "partner_solutions"
    payment_configuration_update = "payment_configuration_update"
    phone_number_name_update = "phone_number_name_update"
    phone_number_quality_update = "phone_number_quality_update"
    security = "security"
    smb_app_state_sync = "smb_app_state_sync"
    smb_message_echoes = "smb_message_echoes"
    template_category_update = "template_category_update"
    user_preferences = "user_preferences"

class Metadata(BaseModel):
    display_phone_number: str
    phone_number_id: str

class Text(BaseModel):
    body: str

class Messages(BaseModel):
    from_: str = Field(alias="from")
    id: str
    timestamp: str
    type: str
    text: Optional[Text] = None

class Value(BaseModel):
    messaging_product: str
    metadata: Metadata
    contacts: Optional[list[Contacts]] = None
    messages: Optional[list[Messages]] = None

class Profile(BaseModel):
    name: Optional[str] = None

class Contacts(BaseModel):
    profile: Optional[Profile] = None
    wa_id: str
    user_id: str

class Changes(BaseModel):
    value: Value
    field: Fields

class Entry(BaseModel):
    id: str
    changes: list[Changes]

class Webhook(BaseModel):
    object: str
    entry: list[Entry]


