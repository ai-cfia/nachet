"""
Validation and existence checking functions for pictures and picture sets.
Implements secure SQL queries using psycopg.sql to prevent SQL injection.
"""

from psycopg import sql


def is_a_picture_set_id(cursor, picture_set_id):
    """
    This function checks if a picture_set_id exists in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture_set_id (str): The UUID of the picture_set to check.
    """
    try:
        stmt = sql.SQL("""
            SELECT EXISTS(
                SELECT 
                    1 
                FROM 
                    {table}
                WHERE 
                    {id_column} = {id_param}
            )
        """).format(
            table=sql.Identifier("picture_set"),
            id_column=sql.Identifier("id"),
            id_param=sql.Literal(picture_set_id),
        )
        cursor.execute(stmt)
        res = cursor.fetchone()[0]
        return res
    except Exception:
        raise Exception("unhandled error")


def is_a_picture_id(cursor, picture_id):
    """
    This function checks if a picture_id exists in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture_id (str): The UUID of the picture to check.
    """
    try:
        stmt = sql.SQL("""
            SELECT EXISTS(
                SELECT 
                    1 
                FROM 
                    {table}
                WHERE 
                    {id_column} = {id_param}
            )
        """).format(
            table=sql.Identifier("picture"),
            id_column=sql.Identifier("id"),
            id_param=sql.Literal(picture_id),
        )
        cursor.execute(stmt)
        res = cursor.fetchone()[0]
        return res
    except Exception:
        raise Exception("unhandled error")
