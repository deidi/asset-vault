from pydantic import BaseModel, Field
from typing import Dict, List

class CategoryExtensionsMap(BaseModel):
    image: List[str] = Field(default_factory=list)
    video: List[str] = Field(default_factory=list)
    audio: List[str] = Field(default_factory=list)
    document: List[str] = Field(default_factory=list)

class FileTypeSettingsResponse(BaseModel):
    categories: Dict[str, List[str]]
    defaults: Dict[str, List[str]]
    counts: Dict[str, int]

class UpdateFileTypeSettingsRequest(BaseModel):
    categories: Dict[str, List[str]]
    recategorize_existing: bool = True

class UpdateFileTypeSettingsResponse(BaseModel):
    status: str
    categories: Dict[str, List[str]]
    recategorized_count: int

class ResetFileTypeSettingsRequest(BaseModel):
    recategorize_existing: bool = True
