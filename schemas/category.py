"""Course category Pydantic models."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class CourseCategory(BaseModel):
    """Course category model."""
    
    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    idnumber: Optional[str] = Field(None, description="Category ID number")
    description: Optional[str] = Field(None, description="Category description")
    descriptionformat: int = Field(1, description="Description format (1=HTML, 0=Plain)")
    parent: int = Field(0, description="Parent category ID (0 for top-level)")
    sortorder: int = Field(0, description="Sort order")
    coursecount: int = Field(0, description="Number of courses in category")
    visible: int = Field(1, description="Visibility (1=visible, 0=hidden)")
    visibleold: int = Field(1, description="Old visibility state")
    timemodified: Optional[datetime] = Field(None, description="Last modification time")
    depth: int = Field(1, description="Depth in category tree")
    path: str = Field("", description="Path (e.g., /1/2/3)")
    theme: Optional[str] = Field(None, description="Category theme")


class CategoryCreate(BaseModel):
    """Model for creating a new category."""
    
    name: str = Field(..., description="Category name", min_length=1, max_length=255)
    parent: Optional[int] = Field(0, description="Parent category ID")
    idnumber: Optional[str] = Field(None, description="Category ID number", max_length=100)
    description: Optional[str] = Field(None, description="Category description")
    descriptionformat: Optional[int] = Field(1, description="Description format")
    theme: Optional[str] = Field(None, description="Category theme")
    
    @field_validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Category name cannot be empty')
        return v.strip()


class CategoryUpdate(BaseModel):
    """Model for updating a category."""
    
    name: Optional[str] = Field(None, description="Category name", min_length=1)
    idnumber: Optional[str] = Field(None, description="Category ID number")
    description: Optional[str] = Field(None, description="Category description")
    descriptionformat: Optional[int] = Field(None, description="Description format")
    parent: Optional[int] = Field(None, description="Parent category ID")
    visible: Optional[bool] = Field(None, description="Visibility")
    theme: Optional[str] = Field(None, description="Category theme")


class CategoryTree(BaseModel):
    """Category tree node."""
    
    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    idnumber: Optional[str] = Field(None, description="Category ID number")
    coursecount: int = Field(0, description="Number of courses")
    visible: int = Field(1, description="Visibility")
    depth: int = Field(1, description="Depth in tree")
    path: str = Field("", description="Path")
    children: List['CategoryTree'] = Field(default_factory=list, description="Child categories")
    
    def count_total_courses(self) -> int:
        """Count total courses including subcategories."""
        total = self.coursecount
        for child in self.children:
            total += child.count_total_courses()
        return total


class CategoryPermission(BaseModel):
    """Category permission/role assignment."""
    
    role_id: int = Field(..., description="Role ID")
    role_name: str = Field(..., description="Role name")
    user_id: int = Field(..., description="User ID")
    context_id: int = Field(..., description="Context ID")
    permission: str = Field("inherit", description="Permission level")


class CategoryMoveOptions(BaseModel):
    """Options for moving categories."""
    
    category_id: int = Field(..., description="Category to move")
    new_parent_id: int = Field(..., description="New parent category ID")
    move_contents: bool = Field(False, description="Move all contents with category")


# Update forward reference
CategoryTree.model_rebuild()