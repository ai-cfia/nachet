"""
Container management operations for user database interactions.
"""

from .exceptions import UserNotFoundError, ContainerNotSetError
from .validation import is_a_user_id


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
        if not is_a_user_id(cursor=cursor, user_id=user_id):
            raise UserNotFoundError(f"User not found for the given id: {user_id}")
        query = """
            UPDATE 
                users
            SET 
                container_url = %s
            WHERE 
                id = %s
            """
        cursor.execute(
            query,
            (
                container_url,
                user_id,
            ),
        )
    except UserNotFoundError:
        raise
    except Exception:
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
        if not is_a_user_id(cursor=cursor, user_id=user_id):
            raise UserNotFoundError(f"User not found for the given id: {user_id}")
        query = """
            SELECT 
                container_url
            FROM 
                users
            WHERE 
                id = %s
            """
        cursor.execute(query, (user_id,))
        res = cursor.fetchone()[0]
        return res
    except TypeError:
        raise ContainerNotSetError(
            "Error: user does not have a container URL under its name"
        )
    except UserNotFoundError as e:
        raise e
    except Exception:
        raise Exception("Error: could not retrieve container url")