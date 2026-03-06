"""User custom fields management service."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from client.moodle_client import AsyncMoodleClient
from schemas.userfield import (
    UserField,
    UserFieldCreate,
    UserFieldUpdate,
    UserFieldCategory,
    UserFieldData,
    UserFieldValue,
)
from client.exceptions import MoodleNotFoundError, MoodleAPIError

logger = logging.getLogger(__name__)


class UserFieldService:
    """Service for user custom fields management."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client
        self._features_available = None

    async def _check_features_available(self) -> bool:
        """Check if user custom fields feature is available."""
        if self._features_available is not None:
            return self._features_available
        
        try:
            # Try to access the feature
            await self.client.call("core_user_get_custom_fields", {})
            self._features_available = True
        except MoodleAPIError as e:
            if "dml_missing_record_exception" in str(e) or "invalidrecord" in str(e):
                logger.info("User custom fields feature is not available in this Moodle instance")
                self._features_available = False
            else:
                # Other error, might be temporary
                self._features_available = None
        except Exception:
            self._features_available = False
        
        return self._features_available or False

    async def list_fields(self, category_id: Optional[int] = None) -> List[UserField]:
        """
        List all user custom fields if available.
        
        Args:
            category_id: Optional filter by category
            
        Returns:
            List of user custom fields (empty if feature not available)
        """
        # Check if feature is available
        if not await self._check_features_available():
            logger.debug("User custom fields feature not available")
            return []
        
        try:
            response = await self.client.call("core_user_get_custom_fields", {})
            
            fields = []
            for field_data in response:
                if category_id and field_data.get("categoryid") != category_id:
                    continue
                fields.append(self._transform_field(field_data))
            
            return fields
            
        except Exception as e:
            logger.debug(f"Failed to list user fields: {e}")
            return []

    async def get_field(self, field_id: int) -> Optional[UserField]:
        """
        Get a specific user custom field if available.
        
        Args:
            field_id: Field ID
            
        Returns:
            User field details or None if not found/available
        """
        fields = await self.list_fields()
        for field in fields:
            if field.id == field_id:
                return field
        
        return None

    async def create_field(self, data: UserFieldCreate) -> Optional[UserField]:
        """
        Create a new user custom field if feature is available.
        
        Args:
            data: Field creation data
            
        Returns:
            Created field or None if feature not available
        """
        if not await self._check_features_available():
            logger.error("Cannot create field: User custom fields feature not available")
            raise RuntimeError("User custom fields feature is not enabled in this Moodle instance")
        
        field_data = data.model_dump(exclude_none=True)
        
        # Handle options for select/menu fields
        if data.datatype in ["menu", "checkbox"] and data.options:
            field_data["param1"] = "\n".join(data.options)
        
        try:
            response = await self.client.call("core_user_create_custom_field", {
                "field": field_data
            })
            
            if not response or "id" not in response:
                raise RuntimeError("Field creation failed")
            
            return await self.get_field(response["id"])
            
        except Exception as e:
            logger.error(f"Failed to create field: {e}")
            raise

    async def update_field(self, field_id: int, data: UserFieldUpdate) -> Optional[UserField]:
        """
        Update an existing user custom field.
        
        Args:
            field_id: Field ID
            data: Update data
            
        Returns:
            Updated field or None if feature not available
        """
        if not await self._check_features_available():
            logger.error("Cannot update field: User custom fields feature not available")
            raise RuntimeError("User custom fields feature is not enabled in this Moodle instance")
        
        update_data = data.model_dump(exclude_none=True)
        update_data["id"] = field_id
        
        # Handle options for select/menu fields
        if data.datatype in ["menu", "checkbox"] and data.options:
            update_data["param1"] = "\n".join(data.options)
        
        try:
            await self.client.call("core_user_update_custom_field", {
                "field": update_data
            })
            
            return await self.get_field(field_id)
            
        except Exception as e:
            logger.error(f"Failed to update field {field_id}: {e}")
            raise

    async def delete_field(self, field_id: int) -> bool:
        """
        Delete a user custom field.
        
        Args:
            field_id: Field ID
            
        Returns:
            True if successful, False if feature not available
        """
        if not await self._check_features_available():
            logger.error("Cannot delete field: User custom fields feature not available")
            return False
        
        try:
            await self.client.call("core_user_delete_custom_field", {
                "fieldid": field_id
            })
            return True
        except Exception as e:
            logger.error(f"Failed to delete field {field_id}: {e}")
            return False

    async def list_categories(self) -> List[UserFieldCategory]:
        """
        List user field categories if available.
        
        Returns:
            List of field categories (empty if feature not available)
        """
        if not await self._check_features_available():
            return []
        
        try:
            response = await self.client.call("core_user_get_custom_field_categories", {})
            
            categories = []
            for cat_data in response:
                categories.append(UserFieldCategory(
                    id=cat_data.get("id", 0),
                    name=cat_data.get("name", ""),
                    sortorder=cat_data.get("sortorder", 0),
                ))
            
            return categories
            
        except Exception as e:
            logger.debug(f"Failed to list field categories: {e}")
            return []

    async def create_category(self, name: str) -> Optional[UserFieldCategory]:
        """
        Create a new user field category.
        
        Args:
            name: Category name
            
        Returns:
            Created category or None if feature not available
        """
        if not await self._check_features_available():
            logger.error("Cannot create category: User custom fields feature not available")
            raise RuntimeError("User custom fields feature is not enabled in this Moodle instance")
        
        try:
            response = await self.client.call("core_user_create_custom_field_category", {
                "name": name
            })
            
            if not response or "id" not in response:
                raise RuntimeError("Category creation failed")
            
            categories = await self.list_categories()
            for cat in categories:
                if cat.id == response["id"]:
                    return cat
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create category: {e}")
            raise

    async def delete_category(self, category_id: int) -> bool:
        """
        Delete a user field category.
        
        Args:
            category_id: Category ID
            
        Returns:
            True if successful, False if feature not available
        """
        if not await self._check_features_available():
            logger.error("Cannot delete category: User custom fields feature not available")
            return False
        
        try:
            await self.client.call("core_user_delete_custom_field_category", {
                "categoryid": category_id
            })
            return True
        except Exception as e:
            logger.error(f"Failed to delete category {category_id}: {e}")
            return False

    async def get_user_field_values(self, user_id: int) -> List[UserFieldValue]:
        """
        Get custom field values for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of field values
        """
        try:
            response = await self.client.call("core_user_get_users_by_field", {
                "field": "id",
                "values": [user_id]
            })
            
            if not response or len(response) == 0:
                raise MoodleNotFoundError("core_user_get_users_by_field", "User", user_id)
            
            user_data = response[0]
            field_values = []
            
            # Extract custom fields from user data
            for key, value in user_data.items():
                if key.startswith("profile_field_"):
                    field_name = key.replace("profile_field_", "")
                    field_values.append(UserFieldValue(
                        user_id=user_id,
                        field_name=field_name,
                        value=value,
                    ))
            
            return field_values
            
        except Exception as e:
            logger.debug(f"Failed to get user field values: {e}")
            return []

    async def set_user_field_value(
        self, 
        user_id: int, 
        field_name: str, 
        value: Any
    ) -> bool:
        """
        Set a custom field value for a user.
        
        Args:
            user_id: User ID
            field_name: Field shortname
            value: Value to set
            
        Returns:
            True if successful
        """
        try:
            # Get user data
            user_data = {
                "id": user_id,
                f"profile_field_{field_name}": value
            }
            
            await self.client.call("core_user_update_users", {
                "users": [user_data]
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set user field value: {e}")
            return False

    async def bulk_set_user_field_values(
        self, 
        user_ids: List[int], 
        field_name: str, 
        value: Any
    ) -> Dict[str, Any]:
        """
        Set a custom field value for multiple users.
        
        Args:
            user_ids: List of user IDs
            field_name: Field shortname
            value: Value to set
            
        Returns:
            Result with success/failure counts
        """
        succeeded = []
        failed = []
        
        for user_id in user_ids:
            try:
                success = await self.set_user_field_value(user_id, field_name, value)
                if success:
                    succeeded.append(user_id)
                else:
                    failed.append((user_id, "Unknown error"))
            except Exception as e:
                failed.append((user_id, str(e)))
        
        return {
            "total": len(user_ids),
            "succeeded": len(succeeded),
            "failed": len(failed),
            "failed_details": failed
        }

    async def get_field_stats(self, field_id: int) -> Dict[str, Any]:
        """
        Get statistics for a custom field.
        
        Args:
            field_id: Field ID
            
        Returns:
            Field statistics
        """
        field = await self.get_field(field_id)
        if not field:
            return {"error": f"Field {field_id} not found"}
        
        # Get all users with non-empty values for this field
        try:
            response = await self.client.call("core_user_get_users", {
                "criteria": [{"key": "custom_field_{}".format(field.shortname), "operator": "IS NOT EMPTY"}]
            })
            
            users_with_value = len(response.get("users", []))
            
            # For select/menu fields, get value distribution
            value_distribution = {}
            if field.datatype in ["menu", "checkbox"] and field.param1:
                options = field.param1 if isinstance(field.param1, list) else str(field.param1).split("\n")
                for option in options:
                    if option.strip():
                        value_distribution[option.strip()] = 0
                
                # Count occurrences
                for user in response.get("users", []):
                    value = user.get(f"profile_field_{field.shortname}")
                    if value and value in value_distribution:
                        value_distribution[value] += 1
            
            return {
                "field_id": field.id,
                "field_name": field.name,
                "field_shortname": field.shortname,
                "datatype": field.datatype,
                "users_with_value": users_with_value,
                "value_distribution": value_distribution if value_distribution else None,
            }
            
        except Exception as e:
            logger.error(f"Failed to get field stats: {e}")
            return {
                "field_id": field.id,
                "field_name": field.name,
                "error": str(e)
            }

    def _transform_field(self, data: Dict[str, Any]) -> UserField:
        """Transform raw field data to model."""
        # Parse options for menu/select fields
        param1 = data.get("param1")
        if data.get("datatype") in ["menu", "checkbox"] and param1:
            if isinstance(param1, str) and "\n" in param1:
                param1 = [p for p in param1.split("\n") if p.strip()]
        
        return UserField(
            id=data.get("id", 0),
            shortname=data.get("shortname", ""),
            name=data.get("name", ""),
            datatype=data.get("datatype", "text"),
            description=data.get("description", ""),
            descriptionformat=data.get("descriptionformat", 1),
            categoryid=data.get("categoryid", 0),
            sortorder=data.get("sortorder", 0),
            required=data.get("required", 0),
            locked=data.get("locked", 0),
            visible=data.get("visible", 2),
            forceunique=data.get("forceunique", 0),
            signup=data.get("signup", 0),
            defaultdata=data.get("defaultdata", ""),
            param1=param1,
            param2=data.get("param2"),
            param3=data.get("param3"),
            param4=data.get("param4"),
            param5=data.get("param5"),
        )