"""User custom fields Pydantic models."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class UserFieldDatatype(str, Enum):
    """User field data types."""
    TEXT = "text"
    CHECKBOX = "checkbox"
    DATE = "date"
    DATETIME = "datetime"
    MENU = "menu"
    TEXTAREA = "textarea"
    RADIO = "radio"
    SELECT = "select"
    MULTISELECT = "multiselect"


class UserField(BaseModel):
    """User custom field model."""
    
    id: int = Field(..., description="Field ID")
    shortname: str = Field(..., description="Field shortname")
    name: str = Field(..., description="Field name")
    datatype: str = Field(..., description="Field data type")
    description: Optional[str] = Field(None, description="Field description")
    descriptionformat: int = Field(1, description="Description format")
    categoryid: int = Field(0, description="Category ID")
    sortorder: int = Field(0, description="Sort order")
    required: int = Field(0, description="Whether field is required")
    locked: int = Field(0, description="Whether field is locked")
    visible: int = Field(2, description="Visibility (2=visible, 1=hidden, 0=not set)")
    forceunique: int = Field(0, description="Whether values must be unique")
    signup: int = Field(0, description="Show on signup page")
    defaultdata: Optional[str] = Field(None, description="Default value")
    param1: Optional[Union[str, List[str]]] = Field(None, description="Parameter 1 (options for menu/select)")
    param2: Optional[str] = Field(None, description="Parameter 2")
    param3: Optional[str] = Field(None, description="Parameter 3")
    param4: Optional[str] = Field(None, description="Parameter 4")
    param5: Optional[str] = Field(None, description="Parameter 5")


class UserFieldCreate(BaseModel):
    """Model for creating a user custom field."""
    
    shortname: str = Field(..., description="Field shortname", min_length=1, max_length=100)
    name: str = Field(..., description="Field name", min_length=1, max_length=255)
    datatype: UserFieldDatatype = Field(..., description="Field data type")
    categoryid: Optional[int] = Field(0, description="Category ID")
    description: Optional[str] = Field(None, description="Field description")
    required: Optional[bool] = Field(False, description="Whether field is required")
    locked: Optional[bool] = Field(False, description="Whether field is locked")
    visible: Optional[bool] = Field(True, description="Whether field is visible")
    forceunique: Optional[bool] = Field(False, description="Whether values must be unique")
    signup: Optional[bool] = Field(False, description="Show on signup page")
    defaultdata: Optional[str] = Field(None, description="Default value")
    options: Optional[List[str]] = Field(None, description="Options for menu/select fields")
    
    @field_validator('shortname')
    def shortname_valid(cls, v):
        if not v.isidentifier():
            raise ValueError('Shortname must be a valid identifier (letters, numbers, underscore)')
        return v
    
    @field_validator('options')
    def validate_options(cls, v, values):
        if 'datatype' in values:
            datatype = values['datatype']
            if datatype in [UserFieldDatatype.MENU, UserFieldDatatype.SELECT, UserFieldDatatype.RADIO]:
                if not v or len(v) < 2:
                    raise ValueError(f'{datatype} fields require at least 2 options')
        return v


class UserFieldUpdate(BaseModel):
    """Model for updating a user custom field."""
    
    name: Optional[str] = Field(None, description="Field name")
    description: Optional[str] = Field(None, description="Field description")
    required: Optional[bool] = Field(None, description="Whether field is required")
    locked: Optional[bool] = Field(None, description="Whether field is locked")
    visible: Optional[bool] = Field(None, description="Whether field is visible")
    forceunique: Optional[bool] = Field(None, description="Whether values must be unique")
    signup: Optional[bool] = Field(None, description="Show on signup page")
    defaultdata: Optional[str] = Field(None, description="Default value")
    options: Optional[List[str]] = Field(None, description="Options for menu/select fields")
    categoryid: Optional[int] = Field(None, description="Category ID")
    sortorder: Optional[int] = Field(None, description="Sort order")
    datatype: Optional[UserFieldDatatype] = Field(None, description="Field data type")


class UserFieldCategory(BaseModel):
    """User field category."""
    
    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    sortorder: int = Field(0, description="Sort order")
    fields: Optional[List[UserField]] = Field(None, description="Fields in this category")


class UserFieldValue(BaseModel):
    """User custom field value."""
    
    user_id: int = Field(..., description="User ID")
    field_name: str = Field(..., description="Field shortname")
    value: Any = Field(None, description="Field value")
    display_value: Optional[str] = Field(None, description="Display value")
    field_id: Optional[int] = Field(None, description="Field ID")


class UserFieldData(BaseModel):
    """User custom field data for multiple users."""
    
    user_id: int = Field(..., description="User ID")
    values: Dict[str, Any] = Field(default_factory=dict, description="Field values keyed by shortname")