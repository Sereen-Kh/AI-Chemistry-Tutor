from pydantic import BaseModel, ConfigDict

class ElementBase(BaseModel):
    atomic_number: int
    symbol: str
    name_ar: str
    name_en: str
    atomic_mass: float | None = None
    category: str | None = None
    period: int | None = None
    group: int | None = None
    electron_configuration: str | None = None

class ElementResponse(ElementBase):
    model_config = ConfigDict(from_attributes=True)
