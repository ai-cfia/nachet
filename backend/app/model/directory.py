from pydantic import BaseModel


class DirectoryRequest(BaseModel):
    container_name: str
