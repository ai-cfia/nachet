import os
import pytest
import tempfile
from unittest.mock import patch, Mock

from app.db.utils import cleanup_temp_db


class TestCleanupTempDb:
    """Test cases for the cleanup_temp_db function."""

    def test_cleanup_temp_db_sqlite_existing_file(self):
        """Test cleanup of an existing SQLite database file."""
        # Create a temporary SQLite file
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(b"fake sqlite data")

        # Verify file exists
        assert os.path.exists(temp_file_path)

        # Create SQLite URL
        sqlite_url = f"sqlite:///{temp_file_path}"

        # Call cleanup function
        cleanup_temp_db(sqlite_url)

        # Verify file was deleted
        assert not os.path.exists(temp_file_path)

    def test_cleanup_temp_db_sqlite_nonexistent_file(self):
        """Test cleanup when SQLite file doesn't exist (should not raise error)."""
        nonexistent_path = "/tmp/nonexistent_database.db"
        sqlite_url = f"sqlite:///{nonexistent_path}"

        # Should not raise an exception
        cleanup_temp_db(sqlite_url)

        # File should still not exist
        assert not os.path.exists(nonexistent_path)

    def test_cleanup_temp_db_postgresql_url(self):
        """Test that PostgreSQL URLs are ignored."""
        postgresql_url = "postgresql://user:pass@localhost:5432/dbname"

        # Should not attempt any file operations
        cleanup_temp_db(postgresql_url)

        # No assertions needed - just verify no exceptions are raised

    def test_cleanup_temp_db_mysql_url(self):
        """Test that MySQL URLs are ignored."""
        mysql_url = "mysql://user:pass@localhost:3306/dbname"

        # Should not attempt any file operations
        cleanup_temp_db(mysql_url)

        # No assertions needed - just verify no exceptions are raised

    def test_cleanup_temp_db_empty_url(self):
        """Test behavior with empty URL string."""
        empty_url = ""

        # Should not attempt any file operations
        cleanup_temp_db(empty_url)

        # No assertions needed - just verify no exceptions are raised

    def test_cleanup_temp_db_sqlite_memory_database(self):
        """Test handling of SQLite in-memory database."""
        memory_url = "sqlite:///:memory:"

        # Should attempt to delete ":memory:" which will fail gracefully
        cleanup_temp_db(memory_url)

        # No assertions needed - just verify no exceptions are raised

    def test_cleanup_temp_db_sqlite_relative_path(self):
        """Test cleanup of SQLite database with relative path."""
        # Create a temporary SQLite file in current directory
        temp_filename = "test_relative.db"

        # Create the file
        with open(temp_filename, "w") as f:
            f.write("fake sqlite data")

        # Verify file exists
        assert os.path.exists(temp_filename)

        # Create SQLite URL with relative path
        sqlite_url = f"sqlite:///{temp_filename}"

        # Call cleanup function
        cleanup_temp_db(sqlite_url)

        # Verify file was deleted
        assert not os.path.exists(temp_filename)

    def test_cleanup_temp_db_sqlite_absolute_path(self):
        """Test cleanup of SQLite database with absolute path."""
        # Create a temporary SQLite file
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_file_path = os.path.abspath(temp_file.name)
            temp_file.write(b"fake sqlite data")

        # Verify file exists
        assert os.path.exists(temp_file_path)

        # Create SQLite URL with absolute path
        sqlite_url = f"sqlite:///{temp_file_path}"

        # Call cleanup function
        cleanup_temp_db(sqlite_url)

        # Verify file was deleted
        assert not os.path.exists(temp_file_path)

    @patch("os.unlink")
    @patch("app.db.utils._get_logger")
    def test_cleanup_temp_db_prints_message(self, mock_get_logger, mock_unlink):
        """Test that cleanup function logs appropriate messages."""
        temp_path = "/tmp/test.db"
        sqlite_url = f"sqlite:///{temp_path}"
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        cleanup_temp_db(sqlite_url)

        # Verify logger was called with expected message
        mock_logger.info.assert_called_once_with(
            "Cleanup temporary database", database_file=temp_path
        )

        # Verify unlink was attempted
        mock_unlink.assert_called_once_with(temp_path)

    @patch("os.unlink")
    def test_cleanup_temp_db_handles_permission_error(self, mock_unlink):
        """Test handling of permission errors during file deletion."""
        mock_unlink.side_effect = PermissionError("Permission denied")

        temp_path = "/tmp/test.db"
        sqlite_url = f"sqlite:///{temp_path}"

        # Should raise PermissionError since it's not caught
        with pytest.raises(PermissionError, match="Permission denied"):
            cleanup_temp_db(sqlite_url)

    @patch("os.unlink")
    def test_cleanup_temp_db_handles_oserror(self, mock_unlink):
        """Test handling of OS errors during file deletion."""
        mock_unlink.side_effect = OSError("Disk full")

        temp_path = "/tmp/test.db"
        sqlite_url = f"sqlite:///{temp_path}"

        # Should raise OSError since it's not caught
        with pytest.raises(OSError, match="Disk full"):
            cleanup_temp_db(sqlite_url)

    def test_cleanup_temp_db_file_not_found_handling(self):
        """Test that FileNotFoundError is properly handled."""
        # Use a path that definitely doesn't exist
        nonexistent_path = "/definitely/does/not/exist/database.db"
        sqlite_url = f"sqlite:///{nonexistent_path}"

        # Should not raise FileNotFoundError
        cleanup_temp_db(sqlite_url)

    # def test_cleanup_temp_db_complex_sqlite_url(self):
    #     """Test parsing of complex SQLite URLs with parameters."""
    #     # Create a temporary SQLite file
    #     with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
    #         temp_file_path = temp_file.name
    #         temp_file.write(b"fake sqlite data")

    #     # Verify file exists
    #     assert os.path.exists(temp_file_path)

    #     # Create SQLite URL with query parameters
    #     sqlite_url = f"sqlite:///{temp_file_path}?cache=shared&mode=rwc"

    #     # Call cleanup function
    #     cleanup_temp_db(sqlite_url)

    #     # Verify file was deleted (function should ignore query params)
    #     assert not os.path.exists(temp_file_path)

    def test_cleanup_temp_db_url_parsing_edge_cases(self):
        """Test URL parsing with various edge cases."""
        test_cases = [
            "sqlite:///",  # Empty path
            "sqlite:////absolute/path.db",  # Four slashes (should work)
            "sqlite://localhost/path.db",  # With host (unusual but should work)
        ]

        for url in test_cases:
            # Should not raise exceptions
            cleanup_temp_db(url)

    def test_cleanup_temp_db_path_extraction(self):
        """Test correct path extraction from SQLite URLs."""
        test_cases = [
            ("sqlite:///test.db", "test.db"),
            ("sqlite:///path/to/test.db", "path/to/test.db"),
            ("sqlite:////absolute/path/test.db", "/absolute/path/test.db"),
            ("sqlite:///:memory:", ":memory:"),
        ]

        with patch("os.unlink") as mock_unlink:
            for url, expected_path in test_cases:
                mock_unlink.reset_mock()

                try:
                    cleanup_temp_db(url)
                    mock_unlink.assert_called_once_with(expected_path)
                except FileNotFoundError:
                    # Expected for :memory: and other non-existent paths
                    pass

    def test_cleanup_temp_db_idempotent_behavior(self):
        """Test that calling cleanup multiple times is safe (idempotent)."""
        # Create a temporary SQLite file
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(b"fake sqlite data")

        sqlite_url = f"sqlite:///{temp_file_path}"

        # First cleanup should delete the file
        cleanup_temp_db(sqlite_url)
        assert not os.path.exists(temp_file_path)

        # Second cleanup should not raise error (idempotent)
        cleanup_temp_db(sqlite_url)
        assert not os.path.exists(temp_file_path)

        # Third cleanup should also not raise error
        cleanup_temp_db(sqlite_url)
        assert not os.path.exists(temp_file_path)

    def test_cleanup_temp_db_various_sqlite_formats(self):
        """Test various SQLite URL formats."""
        test_urls = [
            "sqlite:///test.db",  # Should match - starts with "sqlite"
            "sqlite+pysqlite:///test.db",  # Should match - starts with "sqlite"
            "SQLITE:///test.db",  # Should not match - different case
            "postgresql:///test.db",  # Should not match - different protocol
        ]

        with patch("os.unlink") as mock_unlink:
            # First URL should attempt cleanup
            cleanup_temp_db(test_urls[0])
            mock_unlink.assert_called_once_with("test.db")

            mock_unlink.reset_mock()

            # Second URL should also attempt cleanup (starts with "sqlite")
            cleanup_temp_db(test_urls[1])
            mock_unlink.assert_called_once_with("test.db")

            mock_unlink.reset_mock()

            # Third URL should not attempt cleanup (case sensitive)
            cleanup_temp_db(test_urls[2])
            mock_unlink.assert_not_called()

            # Fourth URL should not attempt cleanup (different protocol)
            cleanup_temp_db(test_urls[3])
            mock_unlink.assert_not_called()

    @patch("builtins.print")
    def test_cleanup_temp_db_no_print_for_non_sqlite(self, mock_print):
        """Test that no message is printed for non-SQLite URLs."""
        postgresql_url = "postgresql://user:pass@localhost:5432/dbname"

        cleanup_temp_db(postgresql_url)

        # Should not print anything for non-SQLite URLs
        mock_print.assert_not_called()

    def test_cleanup_temp_db_with_directory_structure(self):
        """Test cleanup when database file is in a subdirectory."""
        # Create a temporary directory and file
        with tempfile.TemporaryDirectory() as temp_dir:
            db_file = os.path.join(temp_dir, "subdir", "test.db")
            os.makedirs(os.path.dirname(db_file), exist_ok=True)

            with open(db_file, "w") as f:
                f.write("fake sqlite data")

            # Verify file exists
            assert os.path.exists(db_file)

            # Create SQLite URL
            sqlite_url = f"sqlite:///{db_file}"

            # Call cleanup function
            cleanup_temp_db(sqlite_url)

            # Verify file was deleted
            assert not os.path.exists(db_file)
            # Directory should still exist
            assert os.path.exists(os.path.dirname(db_file))
