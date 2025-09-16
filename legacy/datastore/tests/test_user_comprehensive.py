"""
Comprehensive test suite for datastore.db.queries.user module.
This test suite aims to achieve 100% test coverage for all user-related database operations.
"""

import unittest
import uuid
from unittest.mock import MagicMock, patch

from datastore.db.queries.user import (
    UserCreationError,
    UserNotFoundError,
    ContainerNotSetError,
    is_user_registered,
    is_a_user_id,
    get_user_id,
    register_user,
    link_container,
    get_container_url,
    set_default_picture_set,
    get_default_picture_set,
)


class TestUserQueries(unittest.TestCase):
    """Test class for user query functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_cursor = MagicMock()
        self.test_email = "test@example.com"
        self.test_user_id = str(uuid.uuid4())
        self.test_container_url = "https://test-container.blob.core.windows.net/"
        self.test_default_id = str(uuid.uuid4())

    def test_is_user_registered_true(self):
        """Test is_user_registered returns True for existing user."""
        self.mock_cursor.fetchone.return_value = [True]

        result = is_user_registered(self.mock_cursor, self.test_email)

        self.assertTrue(result)
        self.mock_cursor.execute.assert_called_once()
        self.mock_cursor.fetchone.assert_called_once()

    def test_is_user_registered_false(self):
        """Test is_user_registered returns False for non-existing user."""
        self.mock_cursor.fetchone.return_value = [False]

        result = is_user_registered(self.mock_cursor, self.test_email)

        self.assertFalse(result)
        self.mock_cursor.execute.assert_called_once()
        self.mock_cursor.fetchone.assert_called_once()

    def test_is_user_registered_exception(self):
        """Test is_user_registered raises exception on database error."""
        self.mock_cursor.execute.side_effect = Exception("Database error")

        with self.assertRaises(Exception) as context:
            is_user_registered(self.mock_cursor, self.test_email)

        self.assertIn("could not check if the email", str(context.exception))

    def test_is_a_user_id_true(self):
        """Test is_a_user_id returns True for existing user ID."""
        self.mock_cursor.fetchone.return_value = [True]

        result = is_a_user_id(self.mock_cursor, self.test_user_id)

        self.assertTrue(result)
        self.mock_cursor.execute.assert_called_once()
        self.mock_cursor.fetchone.assert_called_once()

    def test_is_a_user_id_false(self):
        """Test is_a_user_id returns False for non-existing user ID."""
        self.mock_cursor.fetchone.return_value = [False]

        result = is_a_user_id(self.mock_cursor, self.test_user_id)

        self.assertFalse(result)
        self.mock_cursor.execute.assert_called_once()
        self.mock_cursor.fetchone.assert_called_once()

    def test_is_a_user_id_exception(self):
        """Test is_a_user_id raises exception on database error."""
        self.mock_cursor.execute.side_effect = Exception("Database error")

        with self.assertRaises(Exception) as context:
            is_a_user_id(self.mock_cursor, self.test_user_id)

        self.assertIn("could not check if", str(context.exception))

    def test_get_user_id_success(self):
        """Test get_user_id returns user ID for existing user."""
        self.mock_cursor.fetchone.return_value = [self.test_user_id]

        result = get_user_id(self.mock_cursor, self.test_email)

        self.assertEqual(result, self.test_user_id)
        self.mock_cursor.execute.assert_called_once()
        self.mock_cursor.fetchone.assert_called_once()

    def test_get_user_id_not_found(self):
        """Test get_user_id raises UserNotFoundError for non-existing user."""
        self.mock_cursor.fetchone.return_value = None

        with self.assertRaises(UserNotFoundError) as context:
            get_user_id(self.mock_cursor, self.test_email)

        self.assertIn("could not be retrieved", str(context.exception))

    def test_get_user_id_general_exception(self):
        """Test get_user_id raises generic exception on database error."""
        self.mock_cursor.execute.side_effect = Exception("Database error")

        with self.assertRaises(Exception) as context:
            get_user_id(self.mock_cursor, self.test_email)

        self.assertEqual(str(context.exception), "Unhandled Error")

    def test_register_user_success(self):
        """Test register_user creates new user and returns UUID."""
        expected_uuid = uuid.uuid4()
        self.mock_cursor.fetchone.return_value = [expected_uuid]

        result = register_user(self.mock_cursor, self.test_email)

        self.assertEqual(result, expected_uuid)
        self.mock_cursor.execute.assert_called_once()
        self.mock_cursor.fetchone.assert_called_once()

    def test_register_user_exception(self):
        """Test register_user raises UserCreationError on database error."""
        self.mock_cursor.execute.side_effect = Exception("Database error")

        with self.assertRaises(UserCreationError) as context:
            register_user(self.mock_cursor, self.test_email)

        self.assertIn("not registered", str(context.exception))

    @patch("datastore.db.queries.user.container_management.is_a_user_id")
    def test_link_container_success(self, mock_is_user):
        """Test link_container successfully links container to user."""
        mock_is_user.return_value = True

        link_container(self.mock_cursor, self.test_user_id, self.test_container_url)

        mock_is_user.assert_called_once_with(
            cursor=self.mock_cursor, user_id=self.test_user_id
        )
        self.mock_cursor.execute.assert_called_once()

    @patch("datastore.db.queries.user.container_management.is_a_user_id")
    def test_link_container_user_not_found(self, mock_is_user):
        """Test link_container raises UserNotFoundError for non-existing user."""
        mock_is_user.return_value = False

        with self.assertRaises(UserNotFoundError) as context:
            link_container(self.mock_cursor, self.test_user_id, self.test_container_url)

        self.assertIn("User not found for the given id", str(context.exception))

    @patch("datastore.db.queries.user.container_management.is_a_user_id")
    def test_link_container_user_not_found_exception_reraise(self, mock_is_user):
        """Test link_container re-raises UserNotFoundError."""
        mock_is_user.side_effect = UserNotFoundError("User not found")

        with self.assertRaises(UserNotFoundError):
            link_container(self.mock_cursor, self.test_user_id, self.test_container_url)

    @patch("datastore.db.queries.user.container_management.is_a_user_id")
    def test_link_container_general_exception(self, mock_is_user):
        """Test link_container raises generic exception on database error."""
        mock_is_user.return_value = True
        self.mock_cursor.execute.side_effect = Exception("Database error")

        with self.assertRaises(Exception) as context:
            link_container(self.mock_cursor, self.test_user_id, self.test_container_url)

        self.assertIn("could not link container to user", str(context.exception))

    @patch("datastore.db.queries.user.container_management.is_a_user_id")
    def test_get_container_url_success(self, mock_is_user):
        """Test get_container_url returns container URL for existing user."""
        mock_is_user.return_value = True
        self.mock_cursor.fetchone.return_value = [self.test_container_url]

        result = get_container_url(self.mock_cursor, self.test_user_id)

        self.assertEqual(result, self.test_container_url)
        mock_is_user.assert_called_once_with(
            cursor=self.mock_cursor, user_id=self.test_user_id
        )
        self.mock_cursor.execute.assert_called_once()
        self.mock_cursor.fetchone.assert_called_once()

    @patch("datastore.db.queries.user.container_management.is_a_user_id")
    def test_get_container_url_user_not_found(self, mock_is_user):
        """Test get_container_url raises UserNotFoundError for non-existing user."""
        mock_is_user.return_value = False

        with self.assertRaises(UserNotFoundError) as context:
            get_container_url(self.mock_cursor, self.test_user_id)

        self.assertIn("User not found for the given id", str(context.exception))

    @patch("datastore.db.queries.user.container_management.is_a_user_id")
    def test_get_container_url_container_not_set(self, mock_is_user):
        """Test get_container_url raises ContainerNotSetError when container URL is None."""
        mock_is_user.return_value = True
        self.mock_cursor.fetchone.return_value = None

        with self.assertRaises(ContainerNotSetError) as context:
            get_container_url(self.mock_cursor, self.test_user_id)

        self.assertIn("does not have a container URL", str(context.exception))

    @patch("datastore.db.queries.user.container_management.is_a_user_id")
    def test_get_container_url_user_not_found_exception_reraise(self, mock_is_user):
        """Test get_container_url re-raises UserNotFoundError."""
        mock_is_user.side_effect = UserNotFoundError("User not found")

        with self.assertRaises(UserNotFoundError):
            get_container_url(self.mock_cursor, self.test_user_id)

    @patch("datastore.db.queries.user.container_management.is_a_user_id")
    def test_get_container_url_general_exception(self, mock_is_user):
        """Test get_container_url raises generic exception on database error."""
        mock_is_user.return_value = True
        self.mock_cursor.execute.side_effect = Exception("Database error")

        with self.assertRaises(Exception) as context:
            get_container_url(self.mock_cursor, self.test_user_id)

        self.assertIn("could not retrieve container url", str(context.exception))

    @patch("datastore.db.queries.user.picture_set_management.is_a_user_id")
    def test_set_default_picture_set_success(self, mock_is_user):
        """Test set_default_picture_set successfully sets default picture set."""
        mock_is_user.return_value = True

        set_default_picture_set(
            self.mock_cursor, self.test_user_id, self.test_default_id
        )

        mock_is_user.assert_called_once_with(
            cursor=self.mock_cursor, user_id=self.test_user_id
        )
        self.mock_cursor.execute.assert_called_once()

    @patch("datastore.db.queries.user.picture_set_management.is_a_user_id")
    def test_set_default_picture_set_user_not_found(self, mock_is_user):
        """Test set_default_picture_set raises UserNotFoundError for non-existing user."""
        mock_is_user.return_value = False

        with self.assertRaises(UserNotFoundError) as context:
            set_default_picture_set(
                self.mock_cursor, self.test_user_id, self.test_default_id
            )

        self.assertIn("User not found for the given id", str(context.exception))

    @patch("datastore.db.queries.user.picture_set_management.is_a_user_id")
    def test_set_default_picture_set_user_not_found_exception_reraise(
        self, mock_is_user
    ):
        """Test set_default_picture_set re-raises UserNotFoundError."""
        mock_is_user.side_effect = UserNotFoundError("User not found")

        with self.assertRaises(UserNotFoundError):
            set_default_picture_set(
                self.mock_cursor, self.test_user_id, self.test_default_id
            )

    @patch("datastore.db.queries.user.picture_set_management.is_a_user_id")
    def test_set_default_picture_set_general_exception(self, mock_is_user):
        """Test set_default_picture_set raises generic exception on database error."""
        mock_is_user.return_value = True
        self.mock_cursor.execute.side_effect = Exception("Database error")

        with self.assertRaises(Exception) as context:
            set_default_picture_set(
                self.mock_cursor, self.test_user_id, self.test_default_id
            )

        self.assertIn("could not set default value for user", str(context.exception))

    @patch("datastore.db.queries.user.picture_set_management.is_a_user_id")
    def test_get_default_picture_set_success(self, mock_is_user):
        """Test get_default_picture_set returns default picture set for existing user."""
        mock_is_user.return_value = True
        self.mock_cursor.fetchone.return_value = [self.test_default_id]

        result = get_default_picture_set(self.mock_cursor, self.test_user_id)

        self.assertEqual(result, self.test_default_id)
        mock_is_user.assert_called_once_with(
            cursor=self.mock_cursor, user_id=self.test_user_id
        )
        self.mock_cursor.execute.assert_called_once()
        self.mock_cursor.fetchone.assert_called_once()

    @patch("datastore.db.queries.user.picture_set_management.is_a_user_id")
    def test_get_default_picture_set_user_not_found(self, mock_is_user):
        """Test get_default_picture_set raises UserNotFoundError for non-existing user."""
        mock_is_user.return_value = False

        with self.assertRaises(UserNotFoundError) as context:
            get_default_picture_set(self.mock_cursor, self.test_user_id)

        self.assertIn("User not found for the given id", str(context.exception))

    @patch("datastore.db.queries.user.picture_set_management.is_a_user_id")
    def test_get_default_picture_set_not_set(self, mock_is_user):
        """Test get_default_picture_set raises exception when default picture set is None."""
        mock_is_user.return_value = True
        self.mock_cursor.fetchone.return_value = None

        with self.assertRaises(Exception) as context:
            get_default_picture_set(self.mock_cursor, self.test_user_id)

        self.assertIn("does not have a default picture set", str(context.exception))

    @patch("datastore.db.queries.user.picture_set_management.is_a_user_id")
    def test_get_default_picture_set_user_not_found_exception_reraise(
        self, mock_is_user
    ):
        """Test get_default_picture_set re-raises UserNotFoundError."""
        mock_is_user.side_effect = UserNotFoundError("User not found")

        with self.assertRaises(UserNotFoundError):
            get_default_picture_set(self.mock_cursor, self.test_user_id)

    @patch("datastore.db.queries.user.picture_set_management.is_a_user_id")
    def test_get_default_picture_set_general_exception(self, mock_is_user):
        """Test get_default_picture_set raises generic exception on database error."""
        mock_is_user.return_value = True
        self.mock_cursor.execute.side_effect = Exception("Database error")

        with self.assertRaises(Exception) as context:
            get_default_picture_set(self.mock_cursor, self.test_user_id)

        self.assertIn("could not retrieve default picture set", str(context.exception))


class TestUserExceptions(unittest.TestCase):
    """Test class for user exception classes."""

    def test_user_creation_error(self):
        """Test UserCreationError can be raised and caught."""
        with self.assertRaises(UserCreationError):
            raise UserCreationError("Test error")

    def test_user_not_found_error(self):
        """Test UserNotFoundError can be raised and caught."""
        with self.assertRaises(UserNotFoundError):
            raise UserNotFoundError("Test error")

    def test_container_not_set_error(self):
        """Test ContainerNotSetError can be raised and caught."""
        with self.assertRaises(ContainerNotSetError):
            raise ContainerNotSetError("Test error")


if __name__ == "__main__":
    unittest.main()
