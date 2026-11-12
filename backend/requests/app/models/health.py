from pydantic import BaseModel

class Health(BaseModel):
    status: str
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "ok"
            }
        }
    }
