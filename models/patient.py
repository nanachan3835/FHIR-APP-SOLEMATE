from pydantic import BaseModel, Field
from typing import List, Optional


class HumanName(BaseModel):
    use: Optional[str] = Field(None, description="Loại tên (official, usual, nickname, etc.)")
    text: str = Field(..., description="Họ và tên đầy đủ của bệnh nhân")


class Patient(BaseModel):
    resourceType: str = Field("Patient", Literal=True, description="Loại tài nguyên FHIR")
    id: str = Field(..., description="ID duy nhất của bệnh nhân")
    name: List[HumanName] = Field(..., description="Danh sách tên của bệnh nhân")
    gender: Optional[str] = Field(None, pattern="^(male|female|other|unknown)$", description="Giới tính")
    birthDate: Optional[str] = Field(None, description="Ngày sinh của bệnh nhân (YYYY-MM-DD)")
    phone: Optional[str] = Field(None, description="Số điện thoại bệnh nhân")
    address: Optional[str] = Field(None, description="Địa chỉ bệnh nhân")

    class Config:
        json_schema_extra = {
            "example": {
                "resourceType": "Patient",
                "id": "123456",
                "name": [{"use": "official", "text": "Nguyễn Văn A"}],
                "gender": "male",
                "birthDate": "1990-05-20",
                "phone": "0987654321",
                "address": "Hà Nội, Việt Nam"
            }
        }

