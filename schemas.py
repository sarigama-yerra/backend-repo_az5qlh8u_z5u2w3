from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr

class Lead(BaseModel):
    """
    Lead enquiries from website
    Collection name: "lead"
    """
    name: str = Field("", description="Customer name")
    email: Optional[EmailStr] = Field(None, description="Customer email for confirmation")
    phone: Optional[str] = Field(None, description="Contact number")
    postcode: Optional[str] = Field(None, description="Installation postcode")
    project_type: Optional[str] = Field(None, description="Windows / Doors / Bifold / Composite / Sliding")
    message: Optional[str] = Field(None, description="Free-text details about project")
    source: Optional[str] = Field("website", description="Lead source")
    files: Optional[List[dict]] = Field(None, description="Uploaded images metadata")
