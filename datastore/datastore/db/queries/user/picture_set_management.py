"""
Picture set management operations for user database interactions.
"""

from psycopg import sql
from .exceptions import UserNotFoundError
from .validation import is_a_user_id
from .security import validate_user_id, sanitize_query_log


def set_default_picture_set(cursor, user_id: str, default_id: str):
    """
    This function sets the default value of a user.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user.
    - default_id (str): The default picture set id.

    Returns:
    - None
    """
    try:
        # Validate and sanitize inputs
        validated_user_id = validate_user_id(user_id)
        validated_default_id = validate_user_id(
            default_id
        )  # picture set IDs are also UUIDs

        # Check if user exists
        if not is_a_user_id(cursor=cursor, user_id=validated_user_id):
            raise UserNotFoundError(f"User not found for the given id {validated_user_id}")

        # Use sql.SQL for secure query composition
        stmt = sql.SQL("""
            UPDATE 
                {table_name}
            SET 
                {default_set_column} = {default_id_param}
            WHERE 
                {id_column} = {user_id_param}
        """).format(
            table_name=sql.Identifier("users"),
            default_set_column=sql.Identifier("default_set_id"),
            id_column=sql.Identifier("id"),
            default_id_param=sql.Literal(validated_default_id),
            user_id_param=sql.Literal(validated_user_id),
        )

        cursor.execute(stmt)
    except UserNotFoundError:
        raise
    except Exception:
        # Log the sanitized query for security monitoring
        if "stmt" in locals():
            print(
                f"Security log: {sanitize_query_log(str(stmt), (validated_default_id, validated_user_id))}"
            )
        raise Exception("Error: could not set default value for user")


def get_default_picture_set(cursor, user_id: str):
    """
    This function retrieves the default picture set of a user.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user

    Returns:
    - The default picture set id of the user.
    """
    try:
        # Validate and sanitize input
        validated_user_id = validate_user_id(user_id)

        # Check if user exists
        if not is_a_user_id(cursor=cursor, user_id=validated_user_id):
            raise UserNotFoundError(f"User not found for the given id {validated_user_id}")

        # Use sql.SQL for secure query composition
        stmt = sql.SQL("""
            SELECT 
                {default_set_column}
            FROM 
                {table_name}
            WHERE 
                {id_column} = {user_id_param}
        """).format(
            table_name=sql.Identifier("users"),
            default_set_column=sql.Identifier("default_set_id"),
            id_column=sql.Identifier("id"),
            user_id_param=sql.Literal(validated_user_id),
        )

        cursor.execute(stmt)
        res = cursor.fetchone()[0]
        return res
    except TypeError:
        raise Exception(
            "Error: user does not have a default picture set under its name"
        )
    except UserNotFoundError as e:
        raise e
    except Exception:
        # Log the sanitized query for security monitoring
        if "stmt" in locals():
            print(
                f"Security log: {sanitize_query_log(str(stmt), (validated_user_id,))}"
            )
        raise Exception("Error: could not retrieve default picture set")
