"""
Comprehensive tests for datastore.db.queries.picture module.
This test suite aims to achieve 100% test coverage for all functions in the picture module.
"""

import pytest
from unittest.mock import Mock, patch
import psycopg
from datastore.db.queries.picture import (
    # Functions to test
    new_picture_set,
    new_picture,
    new_picture_unknown,
    get_picture_set,
    get_picture_set_name,
    get_user_picture_sets,
    get_picture,
    count_pictures,
    get_picture_set_pictures,
    get_validated_pictures,
    is_picture_validated,
    check_picture_inference_exist,
    change_picture_set_id,
    get_user_latest_picture_set,
    update_picture_metadata,
    is_a_picture_set_id,
    is_a_picture_id,
    get_picture_picture_set_id,
    get_picture_set_owner_id,
    update_picture_picture_set_id,
    delete_picture_set,
    get_picture_in_picture_set,
    # Exceptions
    PictureUploadError,
    PictureNotFoundError,
    PictureSetCreationError,
    PictureSetNotFoundError,
    PictureUpdateError,
    GetPictureSetError,
    GetPictureError,
    PictureSetDeleteError,
)


class TestNewPictureSet:
    """Test the new_picture_set function."""

    def test_new_picture_set_success(self):
        """Test successful picture set creation."""
        cursor = Mock()
        cursor.fetchone.return_value = ["test-uuid"]

        picture_set_metadata = '{"test": "data"}'
        user_id = "user-123"
        folder_name = "test-folder"

        result = new_picture_set(cursor, picture_set_metadata, user_id, folder_name)

        assert result == "test-uuid"
        cursor.execute.assert_called_once()
        cursor.fetchone.assert_called_once()

    def test_new_picture_set_without_folder_name(self):
        """Test picture set creation without folder name."""
        cursor = Mock()
        cursor.fetchone.return_value = ["test-uuid"]

        picture_set_metadata = '{"test": "data"}'
        user_id = "user-123"

        result = new_picture_set(cursor, picture_set_metadata, user_id)

        assert result == "test-uuid"
        cursor.execute.assert_called_once()

    def test_new_picture_set_database_error(self):
        """Test picture set creation with database error."""
        cursor = Mock()
        cursor.execute.side_effect = psycopg.Error("Database error")

        picture_set_metadata = '{"test": "data"}'
        user_id = "user-123"

        with pytest.raises(
            PictureSetCreationError, match="Error: picture_set not uploaded"
        ):
            new_picture_set(cursor, picture_set_metadata, user_id)

    def test_new_picture_set_generic_exception(self):
        """Test picture set creation with generic exception."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Generic error")

        picture_set_metadata = '{"test": "data"}'
        user_id = "user-123"

        with pytest.raises(
            PictureSetCreationError, match="Error: picture_set not uploaded"
        ):
            new_picture_set(cursor, picture_set_metadata, user_id)


class TestNewPicture:
    """Test the new_picture function."""

    def test_new_picture_success(self):
        """Test successful picture creation."""
        cursor = Mock()
        cursor.fetchone.return_value = ["picture-uuid"]

        picture = '{"test": "picture"}'
        picture_set_id = "set-123"
        seed_id = "seed-456"
        nb_objects = 5

        result = new_picture(cursor, picture, picture_set_id, seed_id, nb_objects)

        assert result == "picture-uuid"
        assert cursor.execute.call_count == 2  # Two queries
        cursor.fetchone.assert_called_once()

    def test_new_picture_default_objects(self):
        """Test picture creation with default nb_objects."""
        cursor = Mock()
        cursor.fetchone.return_value = ["picture-uuid"]

        picture = '{"test": "picture"}'
        picture_set_id = "set-123"
        seed_id = "seed-456"

        result = new_picture(cursor, picture, picture_set_id, seed_id)

        assert result == "picture-uuid"

    def test_new_picture_database_error(self):
        """Test picture creation with database error."""
        cursor = Mock()
        cursor.execute.side_effect = psycopg.Error("Database error")

        picture = '{"test": "picture"}'
        picture_set_id = "set-123"
        seed_id = "seed-456"

        with pytest.raises(PictureUploadError, match="Error: Picture not uploaded"):
            new_picture(cursor, picture, picture_set_id, seed_id)


class TestNewPictureUnknown:
    """Test the new_picture_unknown function."""

    def test_new_picture_unknown_success(self):
        """Test successful unknown picture creation."""
        cursor = Mock()
        cursor.fetchone.return_value = ["picture-uuid"]

        picture = '{"test": "picture"}'
        picture_set_id = "set-123"
        nb_objects = 3

        result = new_picture_unknown(cursor, picture, picture_set_id, nb_objects)

        assert result == "picture-uuid"
        cursor.execute.assert_called_once()
        cursor.fetchone.assert_called_once()

    def test_new_picture_unknown_database_error(self):
        """Test unknown picture creation with database error."""
        cursor = Mock()
        cursor.execute.side_effect = psycopg.Error("Database error")

        picture = '{"test": "picture"}'
        picture_set_id = "set-123"

        with pytest.raises(PictureUploadError, match="Error: Picture not uploaded"):
            new_picture_unknown(cursor, picture, picture_set_id)


class TestGetPictureSet:
    """Test the get_picture_set function."""

    def test_get_picture_set_success(self):
        """Test successful picture set retrieval."""
        cursor = Mock()
        cursor.fetchone.return_value = ['{"test": "data"}']

        picture_set_id = "set-123"

        result = get_picture_set(cursor, picture_set_id)

        assert result == '{"test": "data"}'
        cursor.execute.assert_called_once()
        cursor.fetchone.assert_called_once()

    def test_get_picture_set_not_found(self):
        """Test picture set retrieval when not found."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Not found")

        picture_set_id = "nonexistent-set"

        with pytest.raises(
            PictureSetNotFoundError,
            match=f"Error: PictureSet not found:{picture_set_id}",
        ):
            get_picture_set(cursor, picture_set_id)


class TestGetPictureSetName:
    """Test the get_picture_set_name function."""

    def test_get_picture_set_name_success(self):
        """Test successful picture set name retrieval."""
        cursor = Mock()
        cursor.fetchone.return_value = ["Test Folder"]

        picture_set_id = "set-123"

        result = get_picture_set_name(cursor, picture_set_id)

        assert result == "Test Folder"
        cursor.execute.assert_called_once()

    def test_get_picture_set_name_null(self):
        """Test picture set name retrieval when name is null."""
        cursor = Mock()
        cursor.fetchone.return_value = [None]

        picture_set_id = "set-123"

        result = get_picture_set_name(cursor, picture_set_id)

        assert result == picture_set_id  # Should return the ID when name is None

    def test_get_picture_set_name_error(self):
        """Test picture set name retrieval with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_set_id = "set-123"

        with pytest.raises(
            PictureSetNotFoundError,
            match=f"Error: PictureSet not found:{picture_set_id}",
        ):
            get_picture_set_name(cursor, picture_set_id)


class TestGetUserPictureSets:
    """Test the get_user_picture_sets function."""

    def test_get_user_picture_sets_success(self):
        """Test successful user picture sets retrieval."""
        cursor = Mock()
        cursor.fetchall.return_value = [("set-1", "Folder 1"), ("set-2", "Folder 2")]
        cursor.rowcount = 2

        user_id = "user-123"

        result = get_user_picture_sets(cursor, user_id)

        assert result == [("set-1", "Folder 1"), ("set-2", "Folder 2")]
        cursor.execute.assert_called_once()

    def test_get_user_picture_sets_no_sets(self):
        """Test user picture sets retrieval when no sets found."""
        cursor = Mock()
        cursor.rowcount = 0

        user_id = "user-123"

        with pytest.raises(
            GetPictureSetError,
            match=f"Error: Error retrieving picture_sets for user:{user_id}",
        ):
            get_user_picture_sets(cursor, user_id)

    def test_get_user_picture_sets_database_error(self):
        """Test user picture sets retrieval with database error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        user_id = "user-123"

        with pytest.raises(
            GetPictureSetError,
            match=f"Error: Error retrieving picture_sets for user:{user_id}",
        ):
            get_user_picture_sets(cursor, user_id)


class TestGetPicture:
    """Test the get_picture function."""

    def test_get_picture_success(self):
        """Test successful picture retrieval."""
        cursor = Mock()
        cursor.fetchone.return_value = ['{"test": "picture"}']

        picture_id = "pic-123"

        result = get_picture(cursor, picture_id)

        assert result == '{"test": "picture"}'
        cursor.execute.assert_called_once()

    def test_get_picture_not_found(self):
        """Test picture retrieval when not found."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Not found")

        picture_id = "nonexistent-pic"

        with pytest.raises(
            PictureNotFoundError, match=f"Error: Picture not found: {picture_id}"
        ):
            get_picture(cursor, picture_id)


class TestCountPictures:
    """Test the count_pictures function."""

    def test_count_pictures_success(self):
        """Test successful picture counting."""
        cursor = Mock()
        cursor.fetchone.return_value = [5]

        picture_set_id = "set-123"

        result = count_pictures(cursor, picture_set_id)

        assert result == 5
        cursor.execute.assert_called_once()

    def test_count_pictures_error(self):
        """Test picture counting with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_set_id = "set-123"

        with pytest.raises(
            PictureSetNotFoundError,
            match=f"Error getting pictures count in picture set : {picture_set_id}",
        ):
            count_pictures(cursor, picture_set_id)


class TestGetPictureSetPictures:
    """Test the get_picture_set_pictures function."""

    def test_get_picture_set_pictures_success(self):
        """Test successful picture set pictures retrieval."""
        cursor = Mock()
        cursor.fetchall.return_value = [
            ("pic-1", '{"data": "1"}'),
            ("pic-2", '{"data": "2"}'),
        ]

        picture_set_id = "set-123"

        result = get_picture_set_pictures(cursor, picture_set_id)

        assert result == [("pic-1", '{"data": "1"}'), ("pic-2", '{"data": "2"}')]
        cursor.execute.assert_called_once()

    def test_get_picture_set_pictures_error(self):
        """Test picture set pictures retrieval with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_set_id = "set-123"

        with pytest.raises(
            GetPictureError,
            match=f"Error: Error while getting pictures for picture_set:{picture_set_id}",
        ):
            get_picture_set_pictures(cursor, picture_set_id)


class TestGetValidatedPictures:
    """Test the get_validated_pictures function."""

    def test_get_validated_pictures_success(self):
        """Test successful validated pictures retrieval."""
        cursor = Mock()
        cursor.fetchall.return_value = [("pic-1",), ("pic-2",), ("pic-3",)]

        picture_set_id = "set-123"

        result = get_validated_pictures(cursor, picture_set_id)

        assert result == ["pic-1", "pic-2", "pic-3"]
        cursor.execute.assert_called_once()

    def test_get_validated_pictures_empty(self):
        """Test validated pictures retrieval with no results."""
        cursor = Mock()
        cursor.fetchall.return_value = []

        picture_set_id = "set-123"

        result = get_validated_pictures(cursor, picture_set_id)

        assert result == []

    def test_get_validated_pictures_error(self):
        """Test validated pictures retrieval with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_set_id = "set-123"

        with pytest.raises(
            GetPictureError,
            match=f"Error: Error while getting validated pictures for picture_set:{picture_set_id}",
        ):
            get_validated_pictures(cursor, picture_set_id)


class TestIsPictureValidated:
    """Test the is_picture_validated function."""

    def test_is_picture_validated_true(self):
        """Test picture validation check returns true."""
        cursor = Mock()
        cursor.fetchone.return_value = [True]

        picture_id = "pic-123"

        result = is_picture_validated(cursor, picture_id)

        assert result is True
        cursor.execute.assert_called_once()

    def test_is_picture_validated_false(self):
        """Test picture validation check returns false."""
        cursor = Mock()
        cursor.fetchone.return_value = [False]

        picture_id = "pic-123"

        result = is_picture_validated(cursor, picture_id)

        assert result is False

    def test_is_picture_validated_error(self):
        """Test picture validation check with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_id = "pic-123"

        with pytest.raises(
            GetPictureError,
            match=f"Error: could not check if the picture {picture_id} is validated",
        ):
            is_picture_validated(cursor, picture_id)


class TestCheckPictureInferenceExist:
    """Test the check_picture_inference_exist function."""

    def test_check_picture_inference_exist_true(self):
        """Test picture inference existence check returns true."""
        cursor = Mock()
        cursor.fetchone.return_value = [True]

        picture_id = "pic-123"

        result = check_picture_inference_exist(cursor, picture_id)

        assert result is True
        cursor.execute.assert_called_once()

    def test_check_picture_inference_exist_false(self):
        """Test picture inference existence check returns false."""
        cursor = Mock()
        cursor.fetchone.return_value = [False]

        picture_id = "pic-123"

        result = check_picture_inference_exist(cursor, picture_id)

        assert result is False

    def test_check_picture_inference_exist_error(self):
        """Test picture inference existence check with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_id = "pic-123"

        with pytest.raises(
            GetPictureError,
            match=f"Error: could not check if the picture {picture_id} has an existing inference",
        ):
            check_picture_inference_exist(cursor, picture_id)


class TestChangePictureSetId:
    """Test the change_picture_set_id function."""

    @patch("datastore.db.queries.picture.picture.get_picture_set_owner_id")
    def test_change_picture_set_id_success(self, mock_get_owner):
        """Test successful picture set ID change."""
        cursor = Mock()
        mock_get_owner.return_value = "user-123"

        user_id = "user-123"
        old_picture_set_id = "old-set"
        new_picture_set_id = "new-set"

        change_picture_set_id(cursor, user_id, old_picture_set_id, new_picture_set_id)

        cursor.execute.assert_called_once()
        assert mock_get_owner.call_count == 2

    @patch("datastore.db.queries.picture.picture.get_picture_set_owner_id")
    def test_change_picture_set_id_old_not_owned(self, mock_get_owner):
        """Test picture set ID change when old set not owned by user."""
        cursor = Mock()
        mock_get_owner.return_value = "other-user"

        user_id = "user-123"
        old_picture_set_id = "old-set"
        new_picture_set_id = "new-set"

        with pytest.raises(
            PictureUpdateError,
            match=f"Error: old picture set not own by user :{user_id}",
        ):
            change_picture_set_id(
                cursor, user_id, old_picture_set_id, new_picture_set_id
            )

    @patch("datastore.db.queries.picture.picture.get_picture_set_owner_id")
    def test_change_picture_set_id_new_not_owned(self, mock_get_owner):
        """Test picture set ID change when new set not owned by user."""
        cursor = Mock()
        # First call returns correct user, second call returns different user
        mock_get_owner.side_effect = ["user-123", "other-user"]

        user_id = "user-123"
        old_picture_set_id = "old-set"
        new_picture_set_id = "new-set"

        with pytest.raises(
            PictureUpdateError,
            match=f"Error: new picture set not own by user :{user_id}",
        ):
            change_picture_set_id(
                cursor, user_id, old_picture_set_id, new_picture_set_id
            )

    @patch("datastore.db.queries.picture.picture.get_picture_set_owner_id")
    def test_change_picture_set_id_database_error(self, mock_get_owner):
        """Test picture set ID change with database error."""
        cursor = Mock()
        mock_get_owner.return_value = "user-123"
        cursor.execute.side_effect = Exception("Database error")

        user_id = "user-123"
        old_picture_set_id = "old-set"
        new_picture_set_id = "new-set"

        with pytest.raises(
            PictureUpdateError,
            match=f"Error: Error while updating pictures for picture_set:{old_picture_set_id}, for user:{user_id}",
        ):
            change_picture_set_id(
                cursor, user_id, old_picture_set_id, new_picture_set_id
            )


class TestGetUserLatestPictureSet:
    """Test the get_user_latest_picture_set function."""

    def test_get_user_latest_picture_set_success(self):
        """Test successful latest picture set retrieval."""
        cursor = Mock()
        cursor.fetchone.return_value = ['{"latest": "set"}']

        user_id = "user-123"

        result = get_user_latest_picture_set(cursor, user_id)

        assert result == '{"latest": "set"}'
        cursor.execute.assert_called_once()

    def test_get_user_latest_picture_set_error(self):
        """Test latest picture set retrieval with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        user_id = "user-123"

        with pytest.raises(
            PictureSetNotFoundError,
            match=f"Error: picture_set not found for user:{user_id}",
        ):
            get_user_latest_picture_set(cursor, user_id)


class TestUpdatePictureMetadata:
    """Test the update_picture_metadata function."""

    def test_update_picture_metadata_success(self):
        """Test successful picture metadata update."""
        cursor = Mock()

        picture_id = "pic-123"
        metadata = {"test": "data"}
        nb_objects = 3

        update_picture_metadata(cursor, picture_id, metadata, nb_objects)

        cursor.execute.assert_called_once()

    def test_update_picture_metadata_error(self):
        """Test picture metadata update with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_id = "pic-123"
        metadata = {"test": "data"}
        nb_objects = 3

        with pytest.raises(
            PictureUpdateError,
            match=f"Error: Picture metadata not updated:{picture_id}",
        ):
            update_picture_metadata(cursor, picture_id, metadata, nb_objects)


class TestIsAPictureSetId:
    """Test the is_a_picture_set_id function."""

    def test_is_a_picture_set_id_true(self):
        """Test picture set ID existence check returns true."""
        cursor = Mock()
        cursor.fetchone.return_value = [True]

        picture_set_id = "set-123"

        result = is_a_picture_set_id(cursor, picture_set_id)

        assert result is True
        cursor.execute.assert_called_once()

    def test_is_a_picture_set_id_false(self):
        """Test picture set ID existence check returns false."""
        cursor = Mock()
        cursor.fetchone.return_value = [False]

        picture_set_id = "nonexistent-set"

        result = is_a_picture_set_id(cursor, picture_set_id)

        assert result is False

    def test_is_a_picture_set_id_error(self):
        """Test picture set ID existence check with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_set_id = "set-123"

        with pytest.raises(Exception, match="unhandled error"):
            is_a_picture_set_id(cursor, picture_set_id)


class TestIsAPictureId:
    """Test the is_a_picture_id function."""

    def test_is_a_picture_id_true(self):
        """Test picture ID existence check returns true."""
        cursor = Mock()
        cursor.fetchone.return_value = [True]

        picture_id = "pic-123"

        result = is_a_picture_id(cursor, picture_id)

        assert result is True
        cursor.execute.assert_called_once()

    def test_is_a_picture_id_false(self):
        """Test picture ID existence check returns false."""
        cursor = Mock()
        cursor.fetchone.return_value = [False]

        picture_id = "nonexistent-pic"

        result = is_a_picture_id(cursor, picture_id)

        assert result is False

    def test_is_a_picture_id_error(self):
        """Test picture ID existence check with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_id = "pic-123"

        with pytest.raises(Exception, match="unhandled error"):
            is_a_picture_id(cursor, picture_id)


class TestGetPicturePictureSetId:
    """Test the get_picture_picture_set_id function."""

    def test_get_picture_picture_set_id_success(self):
        """Test successful picture set ID retrieval from picture."""
        cursor = Mock()
        cursor.fetchone.return_value = ["set-123"]

        picture_id = "pic-123"

        result = get_picture_picture_set_id(cursor, picture_id)

        assert result == "set-123"
        cursor.execute.assert_called_once()

    def test_get_picture_picture_set_id_error(self):
        """Test picture set ID retrieval with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_id = "pic-123"

        with pytest.raises(
            PictureNotFoundError, match=f"Error: Picture not found:{picture_id}"
        ):
            get_picture_picture_set_id(cursor, picture_id)


class TestGetPictureSetOwnerId:
    """Test the get_picture_set_owner_id function."""

    def test_get_picture_set_owner_id_success(self):
        """Test successful picture set owner ID retrieval."""
        cursor = Mock()
        cursor.fetchone.return_value = ["user-123"]

        picture_set_id = "set-123"

        result = get_picture_set_owner_id(cursor, picture_set_id)

        assert result == "user-123"
        cursor.execute.assert_called_once()

    def test_get_picture_set_owner_id_error(self):
        """Test picture set owner ID retrieval with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_set_id = "set-123"

        with pytest.raises(
            PictureSetNotFoundError,
            match=f"Error: PictureSet not found:{picture_set_id}",
        ):
            get_picture_set_owner_id(cursor, picture_set_id)


class TestUpdatePicturePictureSetId:
    """Test the update_picture_picture_set_id function."""

    def test_update_picture_picture_set_id_success(self):
        """Test successful picture set ID update."""
        cursor = Mock()

        picture_id = "pic-123"
        new_picture_set_id = "new-set-456"

        update_picture_picture_set_id(cursor, picture_id, new_picture_set_id)

        cursor.execute.assert_called_once()

    def test_update_picture_picture_set_id_error(self):
        """Test picture set ID update with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_id = "pic-123"
        new_picture_set_id = "new-set-456"

        with pytest.raises(
            PictureUpdateError,
            match=f"Error: Picture picture_set_id not updated:{picture_id}",
        ):
            update_picture_picture_set_id(cursor, picture_id, new_picture_set_id)


class TestDeletePictureSet:
    """Test the delete_picture_set function."""

    def test_delete_picture_set_success(self):
        """Test successful picture set deletion."""
        cursor = Mock()

        picture_set_id = "set-123"

        delete_picture_set(cursor, picture_set_id)

        cursor.execute.assert_called_once()

    def test_delete_picture_set_error(self):
        """Test picture set deletion with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_set_id = "set-123"

        with pytest.raises(
            PictureSetDeleteError,
            match=f"Error: PictureSet not deleted:{picture_set_id}",
        ):
            delete_picture_set(cursor, picture_set_id)


class TestGetPictureInPictureSet:
    """Test the get_picture_in_picture_set function."""

    def test_get_picture_in_picture_set_success(self):
        """Test successful picture retrieval from picture set."""
        cursor = Mock()
        cursor.fetchall.return_value = [('{"pic": "1"}',), ('{"pic": "2"}',)]

        picture_set_id = "set-123"

        result = get_picture_in_picture_set(cursor, picture_set_id)

        assert result == [('{"pic": "1"}',), ('{"pic": "2"}',)]
        cursor.execute.assert_called_once()

    def test_get_picture_in_picture_set_error(self):
        """Test picture retrieval from picture set with error."""
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")

        picture_set_id = "set-123"

        with pytest.raises(
            GetPictureError,
            match=f"Error: Error while getting pictures for picture_set:{picture_set_id}",
        ):
            get_picture_in_picture_set(cursor, picture_set_id)


class TestExceptions:
    """Test that all custom exceptions can be raised."""

    def test_picture_upload_error(self):
        """Test PictureUploadError exception."""
        with pytest.raises(PictureUploadError):
            raise PictureUploadError("Test error")

    def test_picture_not_found_error(self):
        """Test PictureNotFoundError exception."""
        with pytest.raises(PictureNotFoundError):
            raise PictureNotFoundError("Test error")

    def test_picture_set_creation_error(self):
        """Test PictureSetCreationError exception."""
        with pytest.raises(PictureSetCreationError):
            raise PictureSetCreationError("Test error")

    def test_picture_set_not_found_error(self):
        """Test PictureSetNotFoundError exception."""
        with pytest.raises(PictureSetNotFoundError):
            raise PictureSetNotFoundError("Test error")

    def test_picture_update_error(self):
        """Test PictureUpdateError exception."""
        with pytest.raises(PictureUpdateError):
            raise PictureUpdateError("Test error")

    def test_get_picture_set_error(self):
        """Test GetPictureSetError exception."""
        with pytest.raises(GetPictureSetError):
            raise GetPictureSetError("Test error")

    def test_get_picture_error(self):
        """Test GetPictureError exception."""
        with pytest.raises(GetPictureError):
            raise GetPictureError("Test error")

    def test_picture_set_delete_error(self):
        """Test PictureSetDeleteError exception."""
        with pytest.raises(PictureSetDeleteError):
            raise PictureSetDeleteError("Test error")
