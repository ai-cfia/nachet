"""
Tests for OrganizationService role naming logic.
"""

import pytest
import re
from app.service.organization import OrganizationService


class TestOrganizationRoleNaming:
    """Test role name generation."""

    def test_generate_role_name_format(self):
        """Role names should follow the pattern: {type}_{org_prefix}_{random}."""
        org_name = "Test Organization"
        admin_role = OrganizationService._generate_role_name("admin", org_name)
        user_role = OrganizationService._generate_role_name("user", org_name)

        # Pattern: {type}_{alphanumeric_up_to_8}_{8_lowercase_letters}
        pattern = r"^(admin|user)_[a-z0-9]{1,8}_[a-z]{8}$"

        assert re.match(pattern, admin_role), (
            f"Admin role doesn't match pattern: {admin_role}"
        )
        assert re.match(pattern, user_role), (
            f"User role doesn't match pattern: {user_role}"
        )

    def test_generate_role_name_prefix_extraction(self):
        """Role names should extract first 8 alphanumeric chars from org name."""
        # Test with short name
        role = OrganizationService._generate_role_name("admin", "CFIA")
        assert role.startswith("admin_cfia_"), f"Expected 'admin_cfia_', got: {role}"

        # Test with long name
        role = OrganizationService._generate_role_name(
            "admin", "Canadian Food Inspection Agency"
        )
        # Should get "canadian" (8 chars, lowercase, alphanumeric only)
        assert role.startswith("admin_canadian_"), (
            f"Expected 'admin_canadian_', got: {role}"
        )

        # Test with special characters (should be filtered out)
        role = OrganizationService._generate_role_name("admin", "Test-Org!")
        assert role.startswith("admin_testorg_"), (
            f"Expected 'admin_testorg_', got: {role}"
        )

    def test_generate_role_name_random_suffix(self):
        """Random suffix should be 8 lowercase letters."""
        role = OrganizationService._generate_role_name("admin", "Test")

        # Extract the random suffix (last 8 chars)
        parts = role.split("_")
        random_suffix = parts[-1]

        assert len(random_suffix) == 8, (
            f"Random suffix should be 8 chars, got {len(random_suffix)}"
        )
        assert random_suffix.isalpha(), (
            f"Random suffix should be alphabetic only, got: {random_suffix}"
        )
        assert random_suffix.islower(), (
            f"Random suffix should be lowercase, got: {random_suffix}"
        )

    def test_generate_role_name_uniqueness(self):
        """Multiple calls should generate different role names (different random suffixes)."""
        org_name = "Test Organization"

        roles = [
            OrganizationService._generate_role_name("admin", org_name)
            for _ in range(10)
        ]

        # All roles should be unique
        assert len(roles) == len(set(roles)), "Generated role names should be unique"

    def test_generate_role_name_types(self):
        """Should work with both admin and user role types."""
        org_name = "Test"

        admin_role = OrganizationService._generate_role_name("admin", org_name)
        user_role = OrganizationService._generate_role_name("user", org_name)

        assert admin_role.startswith("admin_"), (
            f"Admin role should start with 'admin_', got: {admin_role}"
        )
        assert user_role.startswith("user_"), (
            f"User role should start with 'user_', got: {user_role}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
