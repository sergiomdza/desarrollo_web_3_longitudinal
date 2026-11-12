from datetime import datetime
from pydantic import BaseModel, Field

class Requests(BaseModel):
    id_activo: int | None = Field(default=None)
    name: str
    approved_state: bool
    receive_date: datetime
    return_date: datetime
    confirmation_state: str
    id_responsable: int
    model_config = {
        "json_schema_extra": {
            "example": {
                "id_activo": 1,
                "name": "example",
                "approved_state": True,
                "receive_date": "2026-09-30T10:46:00.000Z",
                "return_date": "2026-10-01T10:46:00.000Z",
                "confirmation_state": "pending",
                "id_responsable": 1
            }
        }
    }
