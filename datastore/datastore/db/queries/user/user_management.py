"""
Core user management operations for database interactions.
"""

from uuid import UUID
from psycopg import sql

from .exceptions import UserCreationError, UserNotFoundError
from .security import validate_email, sanitize_query_log


def get_user_id(cursor, email: str) -> str:
    """
    This function retrieves the UUID of a user.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - email (str): Email of the user

    Returns:
    - The UUID of the user.
    """
    try:
        # Validate and sanitize input
        validated_email = validate_email(email)

        # Use sql.SQL for secure query composition
        stmt = sql.SQL("""
            SELECT 
                {id_column}
            FROM 
                {table_name}
            WHERE 
                {email_column} = {email_param}
        """).format(
            table_name=sql.Identifier("users"),
            id_column=sql.Identifier("id"),
            email_column=sql.Identifier("email"),
            email_param=sql.Literal(validated_email),
        )

        cursor.execute(stmt)
        res = cursor.fetchone()[0]
        return res
    except TypeError:
        raise UserNotFoundError(f"Error: user could not be retrieved for email {validated_email}")
    except Exception:
        # Log the sanitized query for security monitoring
        if "stmt" in locals():
            print(f"Security log: {sanitize_query_log(str(stmt), (validated_email,))}")
        raise Exception("Unhandled Error")


def register_user(cursor, email: str) -> UUID:
    """
    This function registers a user in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - email (str): Email of the user

    Returns:
    - The UUID of the user.
    """
    try:
        # Validate and sanitize input
        validated_email = validate_email(email)

        # Use sql.SQL for secure query composition
        stmt = sql.SQL("""
            INSERT INTO  
                {table_name} ({email_column}, {default_set_column})
            VALUES
                ({email_param}, {null_value})
            RETURNING {id_column}
        """).format(
            table_name=sql.Identifier("users"),
            email_column=sql.Identifier("email"),
            default_set_column=sql.Identifier("default_set_id"),
            id_column=sql.Identifier("id"),
            email_param=sql.Literal(validated_email),
            null_value=sql.SQL("NULL"),
        )

        cursor.execute(stmt)
        return cursor.fetchone()[0]
    except Exception:
        # Log the sanitized query for security monitoring
        if "stmt" in locals():
            print(f"Security log: {sanitize_query_log(str(stmt), (validated_email,))}")
        raise UserCreationError(f"Error: user not registered for email {validated_email}")
