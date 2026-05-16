import json
from datetime import datetime
import os

OUTPUT_DIR = "generated"

def write_requirements_output(session_id, data):

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    file_path = os.path.join(
        OUTPUT_DIR,
        f"requirements_{session_id}.json"
    )

    data["metadata"]["timestamp"] = datetime.utcnow().isoformat()

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

    return file_path