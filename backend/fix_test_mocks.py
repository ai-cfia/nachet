#!/usr/bin/env python3
"""
Script to batch fix RBAC test mocks after refactor.
Replaces old verify_user_has_role pattern with new verify_user_is_cfia_admin pattern.
"""

import re
import sys


def fix_test_file(filepath):
    """Fix RBAC mocks in a test file."""
    with open(filepath, "r") as f:
        content = f.read()

    # Pattern 1: Replace decorator stacks
    # From: @patch("...get_user_organization_id")\n@patch("...verify_user_has_role")
    # To: @patch("...verify_user_is_cfia_admin")
    content = re.sub(
        r'@patch\("([^"]+)\.get_user_organization_id"\)\s*\n\s*@patch\("\1\.verify_user_has_role"\)',
        r'@patch("\1.verify_user_is_cfia_admin")',
        content,
    )

    # Pattern 2: Fix function signatures - remove mock_get_org_id and rename mock_verify_role
    # This is tricky, needs careful handling
    # From: async def test_...(mock_get_session, mock_verify_role, mock_get_org_id, ...
    # To: async def test_...(mock_get_session, mock_verify_cfia_admin, ...
    content = re.sub(
        r"(\basync def test_[^(]+\([^)]*?),\s*mock_verify_role,\s*mock_get_org_id,",
        r"\1, mock_verify_cfia_admin,",
        content,
    )

    # Pattern 3: Remove standalone mock_get_org_id from function params
    content = re.sub(r",\s*mock_get_org_id", "", content)

    # Pattern 4: Fix mock setup inside tests
    # From: mock_get_org_id.return_value = uuid4()\n    mock_verify_role.return_value = None
    # To: mock_verify_cfia_admin.return_value = uuid4()
    content = re.sub(
        r"mock_get_org_id\.return_value = uuid4\(\)\s*\n\s*mock_verify_role\.return_value = None",
        "cfia_org_id = uuid4()\n    mock_verify_cfia_admin.return_value = cfia_org_id",
        content,
    )

    # Pattern 5: Fix mock setup for failure tests
    # From: mock_get_org_id.return_value = uuid4()\n    mock_verify_role.side_effect = HTTPException(...)
    # To: mock_verify_cfia_admin.side_effect = HTTPException(...)
    content = re.sub(
        r"mock_get_org_id\.return_value = uuid4\(\)\s*\n\s*mock_verify_role\.side_effect = HTTPException",
        "mock_verify_cfia_admin.side_effect = HTTPException",
        content,
    )

    # Pattern 6: Fix assertions
    # From: mock_get_org_id.assert_called_once_with(...)\n    mock_verify_role.assert_called_once()
    # To: mock_verify_cfia_admin.assert_called_once_with(...)
    content = re.sub(
        r"mock_get_org_id\.assert_called_once_with\(([^)]+)\)\s*\n\s*mock_verify_role\.assert_called_once\(\)",
        r"mock_verify_cfia_admin.assert_called_once_with(\1)",
        content,
    )

    # Pattern 7: Remove standalone mock_get_org_id assertions
    content = re.sub(
        r"\s*mock_get_org_id\.assert_called_once_with\([^)]+\)\s*\n", "\n", content
    )

    # Write back
    with open(filepath, "w") as f:
        f.write(content)

    print(f"Fixed {filepath}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_test_mocks.py <test_file1> [test_file2] ...")
        sys.exit(1)

    for filepath in sys.argv[1:]:
        fix_test_file(filepath)
