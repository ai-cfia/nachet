"""
User validation functions for database operations.
"""


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
        query = """
            SELECT EXISTS(
                SELECT 
                    1 
                FROM 
                    users
                WHERE 
                    email = %s
            )
                """
        cursor.execute(query, (email,))
        res = cursor.fetchone()[0]
        return res
    except Exception:
        raise Exception(
            f"Error: could not check if the email {email} is a registered user"
        )


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
        query = """
            SELECT EXISTS(
                SELECT 
                    1 
                FROM 
                    users
                WHERE 
                    id = %s
            )
                """
        cursor.execute(query, (user_id,))
        res = cursor.fetchone()[0]
        return res
    except Exception:
        raise Exception(f"Error: could not check if {user_id} given is a user id")