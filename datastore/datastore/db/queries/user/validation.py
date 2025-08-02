"""
User validation functions for database operations.
"""

from psycopg import sql
from .security import validate_email, validate_user_id, sanitize_query_log


def is_user_registered(cursor, email: str) -> bool:
    """
    This function checks if a user is registered in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - email (str): The email of the user.

    Returns:
    - True if the user is registered, False otherwise.
    """
    try:
        # Validate and sanitize input
        validated_email = validate_email(email)

        # Use sql.SQL for secure query composition
        stmt = sql.SQL("""
            SELECT EXISTS(
                SELECT 
                    1 
                FROM 
                    {table_name}
                WHERE 
                    {email_column} = {email_param}
            )
        """).format(
            table_name=sql.Identifier("users"),
            email_column=sql.Identifier("email"),
            email_param=sql.Literal(validated_email),
        )

        cursor.execute(stmt)
        res = cursor.fetchone()[0]
        return res
    except Exception as e:
        # Log the sanitized query for security monitoring
        if "stmt" in locals():
            print(f"Security log: {sanitize_query_log(str(stmt), (validated_email,))}")
        raise Exception(f"Error: could not check if the email is a registered user")


def is_a_user_id(cursor, user_id: str) -> bool:
    """
    This function checks if a user is registered in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user.

    Returns:
    - True if the user is registered, False otherwise.
    """
    try:
        # Validate and sanitize input
        validated_user_id = validate_user_id(user_id)

        # Use sql.SQL for secure query composition
        stmt = sql.SQL("""
            SELECT EXISTS(
                SELECT 
                    1 
                FROM 
                    {table_name}
                WHERE 
                    {id_column} = {user_id_param}
            )
        """).format(
            table_name=sql.Identifier("users"),
            id_column=sql.Identifier("id"),
            user_id_param=sql.Literal(validated_user_id),
        )

        cursor.execute(stmt)
        res = cursor.fetchone()[0]
        return res
    except Exception as e:
        # Log the sanitized query for security monitoring
        if "stmt" in locals():
            print(
                f"Security log: {sanitize_query_log(str(stmt), (validated_user_id,))}"
            )
        raise Exception(f"Error: could not check if given parameter is a user id")
