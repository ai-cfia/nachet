"""
Core user management operations for database interactions.
"""

from uuid import UUID

from .exceptions import UserCreationError, UserNotFoundError


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
        query = """
            SELECT 
                id 
            FROM 
                users
            WHERE 
                email = %s
                """
        cursor.execute(query, (email,))
        res = cursor.fetchone()[0]
        return res
    except TypeError:
        raise UserNotFoundError(f"Error: user {email} could not be retrieved")
    except Exception:
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
        query = """
            INSERT INTO  
                users (email,default_set_id)
            VALUES
                (%s,NULL)
            RETURNING id
            """
        cursor.execute(
            query,
            (email,),
        )
        return cursor.fetchone()[0]
    except Exception:
        raise UserCreationError(f"Error: user {email} not registered")