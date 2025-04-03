from pydantic import BaseModel, Field
from typing import Optional
from abc import ABC

class FHIR(BaseModel, ABC):
    resourceType: str = Field(..., description="Loại tài nguyên FHIR")
    id: Optional[str] = Field(None, description="ID duy nhất của tài nguyên FHIR")

    class Config:
        json_schema_extra = {
            "example": {
                "resourceType": "ResourceType",
                "id": "123456"
            }
        }
