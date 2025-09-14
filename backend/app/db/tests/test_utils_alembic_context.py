import os
import pytest
from pathlib import Path
from unittest.mock import patch

from app.db.utils import alembic_directory_context


class TestAlembicDirectoryContext:
    """Test cases for the alembic_directory_context function."""

    def test_alembic_directory_context_changes_directory(self):
        """Test that the context manager changes to the db directory."""
        # original_cwd = os.getcwd()

        with alembic_directory_context() as db_dir:
            current_cwd = os.getcwd()
            # Verify we're in the db directory
            assert current_cwd.endswith("app/db") or current_cwd.endswith("app\\db")
            assert db_dir == current_cwd
            # If we were already in the db directory, it should stay the same
            # If we were in a different directory, it should have changed
            db_path = Path(__file__).parent.parent.resolve()
            assert Path(current_cwd).resolve() == db_path

    def test_alembic_directory_context_restores_directory(self):
        """Test that the original directory is restored after context exit."""
        original_cwd = os.getcwd()

        with alembic_directory_context():
            # Directory should be in the db directory
            current_cwd = os.getcwd()
            assert current_cwd.endswith("app/db") or current_cwd.endswith("app\\db")

        # Directory should be restored after context exit
        assert os.getcwd() == original_cwd

    def test_alembic_directory_context_yields_db_path(self):
        """Test that the context manager yields the correct db directory path."""
        with alembic_directory_context() as db_dir:
            # The yielded path should be the current working directory inside context
            assert db_dir == os.getcwd()
            # The path should end with the db directory
            assert db_dir.endswith("app/db") or db_dir.endswith("app\\db")
            # The path should be absolute
            assert os.path.isabs(db_dir)

    def test_alembic_directory_context_exception_handling(self):
        """Test that directory is restored even when exception occurs inside context."""
        original_cwd = os.getcwd()

        with pytest.raises(ValueError, match="Test exception"):
            with alembic_directory_context():
                # Verify we're in the db directory
                current_cwd = os.getcwd()
                assert current_cwd.endswith("app/db") or current_cwd.endswith("app\\db")
                # Raise an exception to test cleanup
                raise ValueError("Test exception")

        # Directory should still be restored after exception
        assert os.getcwd() == original_cwd

    def test_alembic_directory_context_nested_calls(self):
        """Test behavior with nested context manager calls."""
        original_cwd = os.getcwd()

        with alembic_directory_context() as outer_db_dir:
            outer_cwd = os.getcwd()

            with alembic_directory_context() as inner_db_dir:
                inner_cwd = os.getcwd()
                # Both should be in the same db directory
                assert outer_cwd == inner_cwd
                assert outer_db_dir == inner_db_dir
                # Both should be in the db directory
                assert inner_cwd.endswith("app/db") or inner_cwd.endswith("app\\db")

            # After inner context, should still be in db directory
            assert os.getcwd() == outer_cwd

        # After both contexts, should be back to original
        assert os.getcwd() == original_cwd

    def test_alembic_directory_context_with_file_operations(self):
        """Test that file operations work correctly within the context."""
        with alembic_directory_context() as db_dir:
            # Verify we can perform file operations in the db directory
            current_files = os.listdir(".")
            db_path = Path(db_dir)
            expected_files = os.listdir(db_path)

            # The files we see should match the actual db directory contents
            assert set(current_files) == set(expected_files)

            # Common files that should exist in the db directory
            expected_items = ["alembic.ini", "alembic", "utils.py"]
            for item in expected_items:
                if os.path.exists(os.path.join(db_path, item)):
                    assert item in current_files

    def test_alembic_directory_context_path_resolution(self):
        """Test that the context resolves to the correct absolute path."""
        with alembic_directory_context() as db_dir:
            # Get the expected path by resolving from utils.py location
            utils_file = Path(__file__).parent.parent / "utils.py"
            expected_db_dir = utils_file.parent.resolve()

            # The yielded path should match the expected db directory
            assert Path(db_dir).resolve() == expected_db_dir

    @patch("os.getcwd")
    @patch("os.chdir")
    def test_alembic_directory_context_mocked_operations(self, mock_chdir, mock_getcwd):
        """Test the context manager with mocked os operations for isolation."""
        # Setup mocks
        mock_getcwd.side_effect = ["/original/path", "/app/db", "/app/db"]

        with alembic_directory_context():
            # Verify chdir was called to change to db directory
            mock_chdir.assert_called()
            # The first call should be to the db directory
            first_call_args = mock_chdir.call_args_list[0][0]
            assert len(first_call_args) == 1
            assert first_call_args[0].endswith("app/db") or first_call_args[0].endswith(
                "app\\db"
            )

        # Verify chdir was called again to restore original directory
        assert mock_chdir.call_count == 2
        mock_chdir.assert_any_call("/original/path")

    def test_alembic_directory_context_preserves_permissions(self):
        """Test that directory changes don't affect file permissions or access."""
        original_cwd = os.getcwd()

        # Check if we can write to original directory
        original_writable = os.access(original_cwd, os.W_OK)

        with alembic_directory_context() as db_dir:
            # Check permissions in db directory
            db_readable = os.access(db_dir, os.R_OK)
            assert db_readable, "Should be able to read from db directory"

        # After context, original directory access should be unchanged
        assert os.access(original_cwd, os.W_OK) == original_writable

    def test_alembic_directory_context_from_different_directory(self):
        """Test the context manager when starting from a different directory."""
        import tempfile

        original_cwd = os.getcwd()

        # Create and change to a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            temp_cwd = os.getcwd()

            # Verify we're in the temp directory
            assert temp_cwd != original_cwd
            assert temp_cwd == temp_dir

            # Now use the context manager
            with alembic_directory_context() as db_dir:
                context_cwd = os.getcwd()
                # Should now be in the db directory
                assert context_cwd != temp_cwd
                assert context_cwd.endswith("app/db") or context_cwd.endswith("app\\db")
                assert db_dir == context_cwd

            # Should be back to temp directory
            assert os.getcwd() == temp_cwd

        # Restore original directory
        os.chdir(original_cwd)
