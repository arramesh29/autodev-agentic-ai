from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter()

BASE_DIR = r"C:\Users\rames\autodev_agentic-ai\generated"

@router.get("/files/{filename}")
def get_file(filename: str):

    file_path = os.path.join(
        BASE_DIR,
        filename
    )

    if not os.path.exists(file_path):
        return {"error": "File not found"}

    with open(file_path, "r") as f:
        content = f.read()

    return {
        "filename": filename,
        "content": content
    }


@router.get("/files/download/{filename}")
def download_file(filename: str):

    file_path = os.path.join(
        BASE_DIR,
        filename
    )

    if not os.path.exists(file_path):

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )
