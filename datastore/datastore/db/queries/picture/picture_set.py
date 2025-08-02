"""
Picture set related database operations.
Implements secure SQL queries using psycopg.sql to prevent SQL injection.
"""

from psycopg import sql
from .exceptions import (
    PictureSetCreationError,
    PictureSetNotFoundError,
    GetPictureSetError,
    PictureSetDeleteError,
)


def new_picture_set(
    cursor, picture_set_metadata, user_id: str, folder_name: str = None
):
    """
    This function uploads a new PictureSet to the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture_set_metadata (json -> str): The PictureSet to upload. Must be formatted as a json
    - user_id (str): The UUID of the user uploading.
    - folder_name (str, optional): The name of the folder. Defaults to None.

    Returns:
    - The UUID of the picture_set.
    """
    try:
        stmt = sql.SQL("""
            INSERT INTO 
                {table}(
                    {picture_set_col},
                    {owner_id_col},
                    {name_col}
                    )
            VALUES
                ({picture_set_param}, {owner_id_param}, {name_param})
            RETURNING {id_col}
            """).format(
            table=sql.Identifier("picture_set"),
            picture_set_col=sql.Identifier("picture_set"),
            owner_id_col=sql.Identifier("owner_id"),
            name_col=sql.Identifier("name"),
            id_col=sql.Identifier("id"),
            picture_set_param=sql.Literal(picture_set_metadata),
            owner_id_param=sql.Literal(user_id),
            name_param=sql.Literal(folder_name),
        )
        cursor.execute(stmt)
        return cursor.fetchone()[0]
    except Exception:
        raise PictureSetCreationError("Error: picture_set not uploaded")


def get_picture_set(cursor, picture_set_id: str):
    """
    This function retrieves a PictureSet from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture_set_id (str): The UUID of the PictureSet to retrieve.

    Returns:
    - The PictureSet in json format.
    """
    try:
        stmt = sql.SQL("""
            SELECT
                {picture_set_col}
            FROM
                {table}
            WHERE
                {id_col} = {id_param}
                """).format(
            table=sql.Identifier("picture_set"),
            picture_set_col=sql.Identifier("picture_set"),
            id_col=sql.Identifier("id"),
            id_param=sql.Literal(picture_set_id),
        )
        cursor.execute(stmt)
        return cursor.fetchone()[0]
    except Exception:
        raise PictureSetNotFoundError(f"Error: PictureSet not found:{picture_set_id}")


def get_picture_set_name(cursor, picture_set_id: str):
    """
    This function retrieves the name of a PictureSet from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user to retrieve the picture_set from (the owner).
    - picture_set_id (str): The UUID of the PictureSet to retrieve.

    Returns:
    - The name of the PictureSet.
    """
    try:
        stmt = sql.SQL("""
            SELECT
                {name_col}
            FROM
                {table}
            WHERE
                {id_col} = {id_param}
                """).format(
            table=sql.Identifier("picture_set"),
            name_col=sql.Identifier("name"),
            id_col=sql.Identifier("id"),
            id_param=sql.Literal(picture_set_id),
        )
        cursor.execute(stmt)
        name = cursor.fetchone()[0]
        return name if name is not None else picture_set_id
    except Exception:
        raise PictureSetNotFoundError(f"Error: PictureSet not found:{picture_set_id}")


def get_user_picture_sets(cursor, user_id: str):
    """
    This function retrieves all the PictureSets of a specific user from the database.

    Args:
    - cursor (cursor): The cursor of the database.
    - user_id (str): uuid of the user
    """
    try:
        stmt = sql.SQL("""
            SELECT
                {id_col},
                {name_col}
            FROM
                {table}
            WHERE
                {owner_id_col} = {owner_id_param}
            """).format(
            table=sql.Identifier("picture_set"),
            id_col=sql.Identifier("id"),
            name_col=sql.Identifier("name"),
            owner_id_col=sql.Identifier("owner_id"),
            owner_id_param=sql.Literal(user_id),
        )
        cursor.execute(stmt)
        if cursor.rowcount == 0:
            raise GetPictureSetError(f"Error: PictureSet not found for user:{user_id}")
        return cursor.fetchall()
    except Exception:
        raise GetPictureSetError(
            f"Error: Error retrieving picture_sets for user:{user_id}"
        )


def get_user_latest_picture_set(cursor, user_id: str):
    """
    This function retrieves the latest picture_set of a specific user from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user to retrieve the picture_set from (the owner).

    Returns:
    - The picture_set in json format.
    """
    try:
        stmt = sql.SQL("""
            SELECT
                {picture_set_col}
            FROM
                {table}
            WHERE
                {owner_id_col} = {owner_id_param}
            ORDER BY
                {upload_date_col}
            DESC
            LIMIT 1
                """).format(
            table=sql.Identifier("picture_set"),
            picture_set_col=sql.Identifier("picture_set"),
            owner_id_col=sql.Identifier("owner_id"),
            upload_date_col=sql.Identifier("upload_date"),
            owner_id_param=sql.Literal(user_id),
        )
        cursor.execute(stmt)
        return cursor.fetchone()[0]
    except Exception:
        raise PictureSetNotFoundError(
            f"Error: picture_set not found for user:{user_id} "
        )


def get_picture_set_owner_id(cursor, picture_set_id):
    """
    This function retrieves the owner_id of a picture_set.

    parameters:
    - cursor (cursor) : The cursor of the database.
    - picture_set_id (str) : The UUID of the picture_set to retrieve the owner_id from.
    """
    try:
        stmt = sql.SQL("""
            SELECT
                {owner_id_col}
            FROM
                {table}
            WHERE
                {id_col} = {id_param}
            """).format(
            table=sql.Identifier("picture_set"),
            owner_id_col=sql.Identifier("owner_id"),
            id_col=sql.Identifier("id"),
            id_param=sql.Literal(picture_set_id),
        )
        cursor.execute(stmt)
        return str(cursor.fetchone()[0])
    except Exception:
        raise PictureSetNotFoundError(f"Error: PictureSet not found:{picture_set_id}")


def delete_picture_set(cursor, picture_set_id):
    """
    This function deletes a picture_set from the database.

    parameters:
    - cursor (cursor) : The cursor of the database.
    - picture_set_id (str) : The UUID of the picture_set to delete.
    """
    try:
        stmt = sql.SQL("""
            DELETE FROM
                {table}
            WHERE
                {id_col} = {id_param}
            """).format(
            table=sql.Identifier("picture_set"),
            id_col=sql.Identifier("id"),
            id_param=sql.Literal(picture_set_id),
        )
        cursor.execute(stmt)
    except Exception:
        raise PictureSetDeleteError(f"Error: PictureSet not deleted:{picture_set_id}")
