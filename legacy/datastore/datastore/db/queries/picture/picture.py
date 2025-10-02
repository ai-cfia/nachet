"""
Individual picture related database operations.
Implements secure SQL queries using psycopg.sql to prevent SQL injection.
"""

from psycopg import sql
from .exceptions import (
    PictureUploadError,
    PictureNotFoundError,
    PictureUpdateError,
    GetPictureError,
    PictureSetNotFoundError,
)
from .picture_set import get_picture_set_owner_id


def new_picture(cursor, picture, picture_set_id: str, seed_id: str, nb_objects=0):
    """
    This function uploads a NEW PICTURE to the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture (str): The Picture METADATA to upload. Must be formatted as a json
    - picture_set_id (str): The UUID of the Picture_set the picture is in.
    - seedID (str): The UUID of the seed the picture is linked to.
    - nb_objects (int): The number of objects in the picture.

    Returns:
    - The UUID of the picture.
    """
    try:
        # Insert picture
        stmt = sql.SQL("""
            INSERT INTO 
                {table}(
                    {picture_col},
                    {picture_set_id_col},
                    {nb_obj_col}
                    )
            VALUES
                ({picture_param}, {picture_set_id_param}, {nb_objects_param})
            RETURNING {id_col}
                """).format(
            table=sql.Identifier("picture"),
            picture_col=sql.Identifier("picture"),
            picture_set_id_col=sql.Identifier("picture_set_id"),
            nb_obj_col=sql.Identifier("nb_obj"),
            id_col=sql.Identifier("id"),
            picture_param=sql.Literal(picture),
            picture_set_id_param=sql.Literal(picture_set_id),
            nb_objects_param=sql.Literal(nb_objects),
        )
        cursor.execute(stmt)
        picture_id = cursor.fetchone()[0]

        # Insert picture_seed relationship
        stmt = sql.SQL("""
            INSERT INTO 
                {table}(
                    {seed_id_col},
                    {picture_id_col}
                    )
            VALUES
                ({seed_id_param}, {picture_id_param})
                """).format(
            table=sql.Identifier("picture_seed"),
            seed_id_col=sql.Identifier("seed_id"),
            picture_id_col=sql.Identifier("picture_id"),
            seed_id_param=sql.Literal(seed_id),
            picture_id_param=sql.Literal(picture_id),
        )
        cursor.execute(stmt)
        return picture_id
    except Exception:
        raise PictureUploadError("Error: Picture not uploaded")


def new_picture_unknown(cursor, picture, picture_set_id: str, nb_objects=0):
    """
    This function uploads a NEW PICTURE to the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture (str): The Picture METADATA to upload. Must be formatted as a json
    - picture_set_id (str): The UUID of the Picture_set the picture is in.
    - nb_objects (int): The number of objects in the picture.

    Returns:
    - The UUID of the picture.
    """
    try:
        stmt = sql.SQL("""
            INSERT INTO 
                {table}(
                    {picture_col},
                    {picture_set_id_col},
                    {nb_obj_col}
                    )
            VALUES
                ({picture_param}, {picture_set_id_param}, {nb_objects_param})
            RETURNING {id_col}
                """).format(
            table=sql.Identifier("picture"),
            picture_col=sql.Identifier("picture"),
            picture_set_id_col=sql.Identifier("picture_set_id"),
            nb_obj_col=sql.Identifier("nb_obj"),
            id_col=sql.Identifier("id"),
            picture_param=sql.Literal(picture),
            picture_set_id_param=sql.Literal(picture_set_id),
            nb_objects_param=sql.Literal(nb_objects),
        )
        cursor.execute(stmt)
        return cursor.fetchone()[0]
    except Exception:
        raise PictureUploadError("Error: Picture not uploaded")


def get_picture(cursor, picture_id: str):
    """
    This function retrieves a Picture from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture_id (str): The UUID of the Picture to retrieve.

    Returns:
    - The Picture in json format.
    """
    try:
        stmt = sql.SQL("""
            SELECT
                {picture_col}
            FROM
                {table}
            WHERE
                {id_col} = {id_param}
                """).format(
            table=sql.Identifier("picture"),
            picture_col=sql.Identifier("picture"),
            id_col=sql.Identifier("id"),
            id_param=sql.Literal(picture_id),
        )
        cursor.execute(stmt)
        return cursor.fetchone()[0]
    except Exception:
        raise PictureNotFoundError(f"Error: Picture not found: {picture_id}")


def count_pictures(cursor, picture_set_id: str):
    """This function retrieves the number of pictures in a picture_set.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture_set_id (str): id of the picture_set to count the pictures from.
    """
    try:
        stmt = sql.SQL("""
            SELECT
                COUNT(*)
            FROM
                {table}
            WHERE
                {picture_set_id_col} = {picture_set_id_param}
            """).format(
            table=sql.Identifier("picture"),
            picture_set_id_col=sql.Identifier("picture_set_id"),
            picture_set_id_param=sql.Literal(picture_set_id),
        )
        cursor.execute(stmt)
        return cursor.fetchone()[0]
    except Exception:
        raise PictureSetNotFoundError(
            f"Error getting pictures count in picture set : {picture_set_id}"
        )


def get_picture_set_pictures(cursor, picture_set_id: str):
    """
    This function retrieves all the pictures of a specific picture_set from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture_set_id (str): The UUID of the PictureSet to retrieve the pictures from.

    Returns:
    - The pictures in json format.
    """
    try:
        stmt = sql.SQL("""
            SELECT
                {id_col},
                {picture_col}
            FROM
                {table}
            WHERE
                {picture_set_id_col} = {picture_set_id_param}
            """).format(
            table=sql.Identifier("picture"),
            id_col=sql.Identifier("id"),
            picture_col=sql.Identifier("picture"),
            picture_set_id_col=sql.Identifier("picture_set_id"),
            picture_set_id_param=sql.Literal(picture_set_id),
        )
        cursor.execute(stmt)
        return cursor.fetchall()
    except Exception:
        raise GetPictureError(
            f"Error: Error while getting pictures for picture_set:{picture_set_id}"
        )


def get_validated_pictures(cursor, picture_set_id: str):
    """
    This functions select pictures from a picture set that have been validated. Therefore, there should exists picture_seed entity for this picture.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture_set_id (str): The UUID of the PictureSet to retrieve the pictures from.
    """
    try:
        stmt = sql.SQL("""
            SELECT
                {p_alias}.{id_col}
            FROM
                {picture_seed_table} {ps_alias}
            JOIN {picture_table} {p_alias} on {ps_alias}.{picture_id_col} = {p_alias}.{id_col}
            WHERE
                {p_alias}.{picture_set_id_col} = {picture_set_id_param}
            """).format(
            picture_seed_table=sql.Identifier("picture_seed"),
            picture_table=sql.Identifier("picture"),
            ps_alias=sql.Identifier("ps"),
            p_alias=sql.Identifier("p"),
            id_col=sql.Identifier("id"),
            picture_id_col=sql.Identifier("picture_id"),
            picture_set_id_col=sql.Identifier("picture_set_id"),
            picture_set_id_param=sql.Literal(picture_set_id),
        )
        cursor.execute(stmt)
        result = [row[0] for row in cursor.fetchall()]
        return result
    except Exception:
        raise GetPictureError(
            f"Error: Error while getting validated pictures for picture_set:{picture_set_id}"
        )


def is_picture_validated(cursor, picture_id: str):
    """
    This functions check if a picture is validated. Therefore, there should exists picture_seed entity for this picture.

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
                    {picture_id_col} = {picture_id_param}
            )
            """).format(
            table=sql.Identifier("picture_seed"),
            picture_id_col=sql.Identifier("picture_id"),
            picture_id_param=sql.Literal(picture_id),
        )
        cursor.execute(stmt)
        result = cursor.fetchone()[0]
        return result
    except Exception:
        raise GetPictureError(
            f"Error: could not check if the picture {picture_id} is validated"
        )


def check_picture_inference_exist(cursor, picture_id: str):
    """
    This functions check whether a picture is associated with an inference.

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
                    {picture_id_col} = {picture_id_param}
            )
            """).format(
            table=sql.Identifier("inference"),
            picture_id_col=sql.Identifier("picture_id"),
            picture_id_param=sql.Literal(picture_id),
        )
        cursor.execute(stmt)
        result = cursor.fetchone()[0]
        return result
    except Exception:
        raise GetPictureError(
            f"Error: could not check if the picture {picture_id} has an existing inference"
        )


def change_picture_set_id(cursor, user_id, old_picture_set_id, new_picture_set_id):
    """
    This function change picture_set_id of all pictures in a picture_set to a new one.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user who want to change the picture_set of pictures (the owner).
    - picture_set_id (str): The UUID of the PictureSet to retrieve the pictures from.
    """
    try:
        if get_picture_set_owner_id(cursor, old_picture_set_id) != user_id:
            raise PictureUpdateError(
                f"Error: old picture set not own by user :{user_id}"
            )
        if get_picture_set_owner_id(cursor, new_picture_set_id) != user_id:
            raise PictureUpdateError(
                f"Error: new picture set not own by user :{user_id}"
            )

        stmt = sql.SQL("""
            UPDATE {table}
            SET {picture_set_id_col} = {new_picture_set_id_param}
            WHERE {picture_set_id_col} = {old_picture_set_id_param}
        """).format(
            table=sql.Identifier("picture"),
            picture_set_id_col=sql.Identifier("picture_set_id"),
            new_picture_set_id_param=sql.Literal(new_picture_set_id),
            old_picture_set_id_param=sql.Literal(old_picture_set_id),
        )
        cursor.execute(stmt)
    except PictureUpdateError as e:
        raise e
    except Exception:
        raise PictureUpdateError(
            f"Error: Error while updating pictures for picture_set:{old_picture_set_id}, for user:{user_id}"
        )


def update_picture_metadata(cursor, picture_id: str, metadata: dict, nb_objects: int):
    """
    This function updates the metadata of a picture in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture_id (str): The UUID of the picture to update.
    - metadata (dict): The metadata to update. Must be formatted as a json.

    Returns:
    - None
    """
    try:
        stmt = sql.SQL("""
            UPDATE
                {table}
            SET
                {picture_col} = {metadata_param},
                {nb_obj_col} = {nb_objects_param}
            WHERE
                {id_col} = {id_param}
            """).format(
            table=sql.Identifier("picture"),
            picture_col=sql.Identifier("picture"),
            nb_obj_col=sql.Identifier("nb_obj"),
            id_col=sql.Identifier("id"),
            metadata_param=sql.Literal(metadata),
            nb_objects_param=sql.Literal(nb_objects),
            id_param=sql.Literal(picture_id),
        )
        cursor.execute(stmt)
    except Exception:
        raise PictureUpdateError(f"Error: Picture metadata not updated:{picture_id}")


def get_picture_picture_set_id(cursor, picture_id):
    """
    This function retrieves the picture_set_id of a picture in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture_id (str): The UUID of the picture to retrieve the picture_set_id from.
    """
    try:
        stmt = sql.SQL("""
            SELECT
                {picture_set_id_col}
            FROM
                {table}
            WHERE
                {id_col} = {id_param}
            """).format(
            table=sql.Identifier("picture"),
            picture_set_id_col=sql.Identifier("picture_set_id"),
            id_col=sql.Identifier("id"),
            id_param=sql.Literal(picture_id),
        )
        cursor.execute(stmt)
        return str(cursor.fetchone()[0])
    except Exception:
        raise PictureNotFoundError(f"Error: Picture not found:{picture_id}")


def update_picture_picture_set_id(cursor, picture_id, new_picture_set_id):
    """
    This function updates the picture_set_id of a picture in the database.

    parameters:
    - cursor (cursor) : The cursor of the database.
    - picture_id (str) : Picture to update.
    - new_picture_set_id (str) : New picture_set_id.
    """
    try:
        stmt = sql.SQL("""
            UPDATE
                {table}
            SET
                {picture_set_id_col} = {new_picture_set_id_param}
            WHERE
                {id_col} = {id_param}
            """).format(
            table=sql.Identifier("picture"),
            picture_set_id_col=sql.Identifier("picture_set_id"),
            id_col=sql.Identifier("id"),
            new_picture_set_id_param=sql.Literal(new_picture_set_id),
            id_param=sql.Literal(picture_id),
        )
        cursor.execute(stmt)
    except Exception:
        raise PictureUpdateError(
            f"Error: Picture picture_set_id not updated:{picture_id}"
        )


def get_picture_in_picture_set(cursor, picture_set_id):
    """
    This function retrieves all the pictures of a specific picture_set from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture_set_id (str): The UUID of the PictureSet to retrieve the pictures from.

    Returns:
    - The pictures in json format.
    """
    try:
        stmt = sql.SQL("""
            SELECT
                {picture_col}
            FROM
                {table}
            WHERE
                {picture_set_id_col} = {picture_set_id_param}
            """).format(
            table=sql.Identifier("picture"),
            picture_col=sql.Identifier("picture"),
            picture_set_id_col=sql.Identifier("picture_set_id"),
            picture_set_id_param=sql.Literal(picture_set_id),
        )
        cursor.execute(stmt)
        return cursor.fetchall()
    except Exception:
        raise GetPictureError(
            f"Error: Error while getting pictures for picture_set:{picture_set_id}"
        )
