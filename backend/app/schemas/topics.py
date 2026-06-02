from pydantic import BaseModel, ConfigDict

class TopicBase(BaseModel):
    title_ar: str
    title_en: str | None = None
    description_ar: str | None = None
    category: str | None = None
    difficulty: int = 1
    icon: str | None = None
    order: int = 0

class TopicCreate(TopicBase):
    pass

class TopicUpdate(BaseModel):
    title_ar: str | None = None
    title_en: str | None = None
    description_ar: str | None = None
    category: str | None = None
    difficulty: int | None = None
    icon: str | None = None
    order: int | None = None

class TopicResponse(TopicBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
