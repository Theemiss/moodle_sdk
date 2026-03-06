"""Course category management service."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from client.moodle_client import AsyncMoodleClient
from schemas.category import (
    CourseCategory,
    CategoryCreate,
    CategoryUpdate,
    CategoryTree,
    CategoryPermission,
)
from client.exceptions import MoodleNotFoundError, MoodlePermissionError

logger = logging.getLogger(__name__)


class CategoryService:
    """Service for course category management operations."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client

    async def list_categories(
        self, 
        parent_id: Optional[int] = None,
        include_hidden: bool = False
    ) -> List[CourseCategory]:
        """
        List all course categories.
        
        Args:
            parent_id: Filter by parent category ID
            include_hidden: Whether to include hidden categories
            
        Returns:
            List of course categories
        """
        params = {}
        if parent_id is not None:
            params["criteria"] = [{"key": "parent", "value": parent_id}]
        
        try:
            response = await self.client.call("core_course_get_categories", params)
            
            categories = []
            for cat_data in response:
                # Filter hidden categories if needed
                if not include_hidden and not cat_data.get("visible", 1):
                    continue
                    
                categories.append(self._transform_category(cat_data))
            
            return categories
            
        except Exception as e:
            logger.error(f"Failed to list categories: {e}")
            return []

    async def get_category(self, category_id: int) -> CourseCategory:
        """
        Get a single category by ID.
        
        Args:
            category_id: Category ID
            
        Returns:
            Course category details
            
        Raises:
            MoodleNotFoundError: If category doesn't exist
        """
        try:
            response = await self.client.call("core_course_get_categories", {
                "criteria": [{"key": "id", "value": category_id}]
            })
            
            if not response or len(response) == 0:
                raise MoodleNotFoundError("core_course_get_categories", "Category", category_id)
            
            return self._transform_category(response[0])
            
        except Exception as e:
            if isinstance(e, MoodleNotFoundError):
                raise
            logger.error(f"Failed to get category {category_id}: {e}")
            raise MoodleNotFoundError("core_course_get_categories", "Category", category_id)

    async def create_category(self, data: CategoryCreate) -> CourseCategory:
        """
        Create a new course category.
        
        Args:
            data: Category creation data
            
        Returns:
            Created category
        """
        category_data = data.model_dump(exclude_none=True)
        
        response = await self.client.call("core_course_create_categories", {
            "categories": [category_data]
        })
        
        if not response or len(response) == 0:
            raise RuntimeError("Category creation returned empty response")
        
        return await self.get_category(response[0]["id"])

    async def update_category(self, category_id: int, data: CategoryUpdate) -> CourseCategory:
        """
        Update an existing category.
        
        Args:
            category_id: Category ID
            data: Update data
            
        Returns:
            Updated category
        """
        update_data = data.model_dump(exclude_none=True)
        update_data["id"] = category_id
        
        await self.client.call("core_course_update_categories", {
            "categories": [update_data]
        })
        
        return await self.get_category(category_id)

    async def delete_category(
        self, 
        category_id: int, 
        new_parent_id: Optional[int] = None,
        recursive: bool = False
    ) -> bool:
        """
        Delete a category.
        
        Args:
            category_id: Category ID to delete
            new_parent_id: Move subcategories to this parent
            recursive: If True, delete all subcategories and courses
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If recursive is False and category has children
        """
        # Check if category has children
        children = await self.list_categories(parent_id=category_id)
        if children and not recursive and not new_parent_id:
            raise ValueError(
                f"Category {category_id} has {len(children)} subcategories. "
                "Use recursive=True to delete all, or specify new_parent_id to move them."
            )
        
        params = {
            "id": category_id,
            "recursive": 1 if recursive else 0,
        }
        
        if new_parent_id:
            params["newparent"] = new_parent_id
        
        try:
            await self.client.call("core_course_delete_categories", {
                "categories": [params]
            })
            return True
        except Exception as e:
            logger.error(f"Failed to delete category {category_id}: {e}")
            return False

    async def move_category(self, category_id: int, new_parent_id: int) -> CourseCategory:
        """
        Move a category to a new parent.
        
        Args:
            category_id: Category ID to move
            new_parent_id: New parent category ID
            
        Returns:
            Updated category
        """
        return await self.update_category(category_id, CategoryUpdate(parent=new_parent_id))

    async def get_category_tree(self, root_id: Optional[int] = None) -> List[CategoryTree]:
        """
        Get hierarchical category tree.
        
        Args:
            root_id: Optional root category ID
            
        Returns:
            Nested category tree
        """
        all_categories = await self.list_categories(include_hidden=True)
        
        # Build lookup dictionary
        category_dict = {cat.id: cat for cat in all_categories}
        
        # Build tree
        roots = []
        for cat in all_categories:
            if root_id is not None:
                if cat.id == root_id:
                    roots.append(self._build_tree(cat, category_dict))
            else:
                if cat.parent == 0:
                    roots.append(self._build_tree(cat, category_dict))
        
        return roots

    async def get_category_permissions(self, category_id: int) -> List[CategoryPermission]:
        """
        Get permissions/roles for a category.
        
        Args:
            category_id: Category ID
            
        Returns:
            List of role assignments
        """
        try:
            # Get context ID for the category
            context_level = 40  # CONTEXT_COURSECAT
            response = await self.client.call("core_role_get_role_assignments", {
                "contextid": 0,  # 0 means get from context level and instance
                "contextlevel": context_level,
                "instanceid": category_id
            })
            
            permissions = []
            for assignment in response:
                permissions.append(CategoryPermission(
                    role_id=assignment.get("roleid", 0),
                    role_name=assignment.get("rolename", ""),
                    user_id=assignment.get("userid", 0),
                    context_id=assignment.get("contextid", 0),
                    permission=assignment.get("permission", "inherit"),
                ))
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get category permissions: {e}")
            return []

    async def assign_role(
        self, 
        category_id: int, 
        user_id: int, 
        role_id: int
    ) -> bool:
        """
        Assign a role to a user in a category context.
        
        Args:
            category_id: Category ID
            user_id: User ID
            role_id: Role ID to assign
            
        Returns:
            True if successful
        """
        try:
            await self.client.call("core_role_assign_roles", {
                "assignments": [{
                    "roleid": role_id,
                    "userid": user_id,
                    "contextlevel": "coursecat",
                    "instanceid": category_id
                }]
            })
            return True
        except Exception as e:
            logger.error(f"Failed to assign role: {e}")
            return False

    async def unassign_role(
        self, 
        category_id: int, 
        user_id: int, 
        role_id: int
    ) -> bool:
        """
        Unassign a role from a user in a category context.
        
        Args:
            category_id: Category ID
            user_id: User ID
            role_id: Role ID to unassign
            
        Returns:
            True if successful
        """
        try:
            await self.client.call("core_role_unassign_roles", {
                "unassignments": [{
                    "roleid": role_id,
                    "userid": user_id,
                    "contextlevel": "coursecat",
                    "instanceid": category_id
                }]
            })
            return True
        except Exception as e:
            logger.error(f"Failed to unassign role: {e}")
            return False

    async def get_category_courses(self, category_id: int) -> List[Dict[str, Any]]:
        """
        Get all courses in a category.
        
        Args:
            category_id: Category ID
            
        Returns:
            List of courses in the category
        """
        try:
            response = await self.client.call("core_course_get_courses_by_field", {
                "field": "category",
                "value": category_id
            })
            
            return response.get("courses", [])
            
        except Exception as e:
            logger.error(f"Failed to get category courses: {e}")
            return []

    def _transform_category(self, data: Dict[str, Any]) -> CourseCategory:
        """Transform raw category data to model."""
        return CourseCategory(
            id=data.get("id", 0),
            name=data.get("name", ""),
            idnumber=data.get("idnumber", ""),
            description=data.get("description", ""),
            descriptionformat=data.get("descriptionformat", 1),
            parent=data.get("parent", 0),
            sortorder=data.get("sortorder", 0),
            coursecount=data.get("coursecount", 0),
            visible=data.get("visible", 1),
            visibleold=data.get("visibleold", 1),
            timemodified=datetime.fromtimestamp(data.get("timemodified", 0)) if data.get("timemodified") else None,
            depth=data.get("depth", 1),
            path=data.get("path", ""),
            theme=data.get("theme"),
        )

    def _build_tree(self, category: CourseCategory, all_cats: Dict[int, CourseCategory]) -> CategoryTree:
        """Recursively build category tree."""
        children = []
        for cat in all_cats.values():
            if cat.parent == category.id:
                children.append(self._build_tree(cat, all_cats))
        
        return CategoryTree(
            id=category.id,
            name=category.name,
            idnumber=category.idnumber,
            coursecount=category.coursecount,
            visible=category.visible,
            depth=category.depth,
            path=category.path,
            children=children
        )