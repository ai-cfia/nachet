"""
Container management operations for user database interactions.
"""

from psycopg import sql
from .exceptions import UserNotFoundError, ContainerNotSetError
from .validation import is_a_user_id
from .security import validate_user_id, validate_container_url, sanitize_query_log


def link_container(cursor, user_id: str, container_url: str):
    """
    This function links a container to a user in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user.
    - container_url (str): The url of the container

    Returns:
    - None
    """
    try:
        # Validate and sanitize inputs
        validated_user_id = validate_user_id(user_id)
        validated_container_url = validate_container_url(container_url)

        # Check if user exists
        if not is_a_user_id(cursor=cursor, user_id=validated_user_id):
            raise UserNotFoundError(f"User not found for the given id {validated_user_id}")

        # Use sql.SQL for secure query composition
        stmt = sql.SQL("""
            UPDATE 
                {table_name}
            SET 
                {container_url_column} = {container_url_param}
            WHERE 
                {id_column} = {user_id_param}
        """).format(
            table_name=sql.Identifier("users"),
            container_url_column=sql.Identifier("container_url"),
            id_column=sql.Identifier("id"),
            container_url_param=sql.Literal(validated_container_url),
            user_id_param=sql.Literal(validated_user_id),
        )

        cursor.execute(stmt)
    except UserNotFoundError:
        raise
    except Exception:
        # Log the sanitized query for security monitoring
        if "stmt" in locals():
            print(
                f"Security log: {sanitize_query_log(str(stmt), (validated_container_url, validated_user_id))}"
            )
        raise Exception("Error: could not link container to user")


def get_container_url(cursor, user_id: str):
    """
    This function retrieves the container url of a user.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user

    Returns:
    - The container url of the user.
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
                {container_url_column}
            FROM 
                {table_name}
            WHERE 
                {id_column} = {user_id_param}
        """).format(
            table_name=sql.Identifier("users"),
            container_url_column=sql.Identifier("container_url"),
            id_column=sql.Identifier("id"),
            user_id_param=sql.Literal(validated_user_id),
        )

        cursor.execute(stmt)
        res = cursor.fetchone()[0]
        return res
    except TypeError:
        raise ContainerNotSetError(
            "Error: user does not have a container URL under its name"
        )
    except UserNotFoundError as e:
        raise e
    except Exception:
        # Log the sanitized query for security monitoring
        if "stmt" in locals():
            print(
                f"Security log: {sanitize_query_log(str(stmt), (validated_user_id,))}"
            )
        raise Exception("Error: could not retrieve container url")
