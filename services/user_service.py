"""User management service."""

import logging
from typing import List, Optional

from client.exceptions import MoodleNotFoundError
from client.moodle_client import AsyncMoodleClient
from schemas.user import MoodleUser, UserRole, UserSearchQuery

logger = logging.getLogger(__name__)


class UserService:
    """Service for user operations."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client

    def _transform_user(self, user_data: dict) -> MoodleUser:
        """Transform raw Moodle user data to Pydantic model."""
        roles = []
        for role in user_data.get("roles", []):
            roles.append(
                UserRole(
                    roleid=role.get("roleid", 0),
                    name=role.get("name", ""),
                    shortname=role.get("shortname", ""),
                    contextid=role.get("contextid", 0),
                    contextlevel=role.get("contextlevel", ""),
                    courseid=role.get("courseid"),
                )
            )

        return MoodleUser(
            id=user_data["id"],
            username=user_data["username"],
            firstname=user_data.get("firstname", ""),
            lastname=user_data.get("lastname", ""),
            fullname=user_data.get("fullname", ""),
            email=user_data.get("email", ""),
            idnumber=user_data.get("idnumber"),
            institution=user_data.get("institution"),
            department=user_data.get("department"),
            phone1=user_data.get("phone1"),
            phone2=user_data.get("phone2"),
            city=user_data.get("city"),
            country=user_data.get("country"),
            lang=user_data.get("lang", "en"),
            timezone=user_data.get("timezone", "99"),
            firstaccess=user_data.get("firstaccess"),
            lastaccess=user_data.get("lastaccess"),
            lastlogin=user_data.get("lastlogin"),
            currentlogin=user_data.get("currentlogin"),
            auth=user_data.get("auth", "manual"),
            confirmed=user_data.get("confirmed", True),
            suspended=user_data.get("suspended", False),
            deleted=user_data.get("deleted", False),
            profileimageurl=user_data.get("profileimageurl"),
            profileimageurlsmall=user_data.get("profileimageurlsmall"),
            roles=roles,
        )

    async def get_user(self, user_id: int) -> MoodleUser:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User object

        Raises:
            MoodleNotFoundError: If user doesn't exist
        """
        response = await self.client.call(
            "core_user_get_users_by_field",
            {"field": "id", "values": [user_id]},
        )

        if not response or len(response) == 0:
            raise MoodleNotFoundError("core_user_get_users_by_field", "User", user_id)

        return self._transform_user(response[0])

    async def search_users(self, query: UserSearchQuery) -> List[MoodleUser]:
        """
        Search for users.

        Args:
            query: Search parameters

        Returns:
            List of matching users
        """
        criteria = []

        if query.query:
            criteria.append({"key": "search", "value": query.query})
        if query.idnumber:
            criteria.append({"key": "idnumber", "value": query.idnumber})
        if query.email:
            criteria.append({"key": "email", "value": query.email})
        if query.username:
            criteria.append({"key": "username", "value": query.username})
        if query.firstname:
            criteria.append({"key": "firstname", "value": query.firstname})
        if query.lastname:
            criteria.append({"key": "lastname", "value": query.lastname})
        if query.courseid:
            criteria.append({"key": "courseid", "value": query.courseid})

        params = {
            "criteria": criteria,
        }

        response = await self.client.call("core_user_get_users", params)

        users = []
        for user_data in response.get("users", []):
            users.append(self._transform_user(user_data))

        # Manual pagination since Moodle doesn't support it well here
        start = query.page * query.limit
        end = start + query.limit
        return users[start:end]

    async def get_user_by_email(self, email: str) -> Optional[MoodleUser]:
        """
        Find user by email address.

        Args:
            email: Email address

        Returns:
            User if found, None otherwise
        """
        response = await self.client.call(
            "core_user_get_users_by_field",
            {"field": "email", "values": [email]},
        )

        if not response or len(response) == 0:
            return None

        return self._transform_user(response[0])

    async def get_user_by_username(self, username: str) -> Optional[MoodleUser]:
        """
        Find user by username.

        Args:
            username: Username

        Returns:
            User if found, None otherwise
        """
        response = await self.client.call(
            "core_user_get_users_by_field",
            {"field": "username", "values": [username]},
        )

        if not response or len(response) == 0:
            return None

        return self._transform_user(response[0])

    async def map_external_user(self, external_id: str, id_field: str = "idnumber") -> Optional[MoodleUser]:
        """
        Find user by external ID mapping.

        Args:
            external_id: External identifier
            id_field: Moodle field to match against (idnumber, username, email)

        Returns:
            User if found, None otherwise
        """
        valid_fields = ["idnumber", "username", "email"]
        if id_field not in valid_fields:
            raise ValueError(f"id_field must be one of: {valid_fields}")

        response = await self.client.call(
            "core_user_get_users_by_field",
            {"field": id_field, "values": [external_id]},
        )

        if not response or len(response) == 0:
            return None

        return self._transform_user(response[0])

    async def get_user_roles(self, user_id: int, course_id: int) -> List[str]:
        """
        Get user's roles in a specific course.

        Args:
            user_id: User ID
            course_id: Course ID

        Returns:
            List of role shortnames
        """
        params = {
            "courseid": course_id,
            "userid": user_id,
        }

        response = await self.client.call("core_enrol_get_enrolled_users", params)

        if not response or len(response) == 0:
            return []

        user_data = response[0]
        roles = [role["shortname"] for role in user_data.get("roles", [])]
        return roles

    async def bulk_get_users(self, user_ids: List[int]) -> List[MoodleUser]:
        """
        Get multiple users by IDs.

        Args:
            user_ids: List of user IDs

        Returns:
            List of users (only found ones)
        """
        if not user_ids:
            return []

        # Process in chunks to avoid URL length limits
        chunk_size = 50
        all_users = []

        for i in range(0, len(user_ids), chunk_size):
            chunk = user_ids[i : i + chunk_size]
            try:
                response = await self.client.call(
                    "core_user_get_users_by_field",
                    {"field": "id", "values": chunk},
                )

                for user_data in response:
                    all_users.append(self._transform_user(user_data))
            except Exception as e:
                logger.error(f"Failed to fetch users chunk: {e}")

        return all_users