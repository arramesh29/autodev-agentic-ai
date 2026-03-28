from fastapi import APIRouter
import os

router = APIRouter()

BASE_DIR = "C:/Users/rames/autodev_build"

@router.get("/files/{filename}")
def get_file(filename: str):
    file_path = os.path.join(BASE_DIR, filename)

    if not os.path.exists(file_path):
        return {"error": "File not found"}

    with open(file_path, "r") as f:
        content = f.read()

    return {
        "filename": filename,
        "content": content
    }
