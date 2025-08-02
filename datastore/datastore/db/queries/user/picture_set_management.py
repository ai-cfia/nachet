"""
Picture set management operations for user database interactions.
"""

from .exceptions import UserNotFoundError
from .validation import is_a_user_id


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
        if not is_a_user_id(cursor=cursor, user_id=user_id):
            raise UserNotFoundError(f"User not found for the given id: {user_id}")
        query = """
            UPDATE 
                users
            SET 
                default_set_id = %s
            WHERE 
                id = %s
            """
        cursor.execute(
            query,
            (
                default_id,
                user_id,
            ),
        )
    except UserNotFoundError:
        raise
    except Exception:
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
        if not is_a_user_id(cursor=cursor, user_id=user_id):
            raise UserNotFoundError(f"User not found for the given id: {user_id}")
        query = """
            SELECT 
                default_set_id
            FROM 
                users
            WHERE 
                id = %s
            """
        cursor.execute(query, (user_id,))
        res = cursor.fetchone()[0]
        return res
    except TypeError:
        raise Exception(
            "Error: user does not have a default picture set under its name"
        )
    except UserNotFoundError as e:
        raise e
    except Exception:
        raise Exception("Error: could not retrieve default picture set")