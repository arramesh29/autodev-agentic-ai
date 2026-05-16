import json
from datetime import datetime
import os

def write_requirements_output(session_id, data):

    BASE_DIR = os.getcwd()

    OUTPUT_DIR = os.path.join(BASE_DIR, "generated")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    file_path = os.path.join(
        OUTPUT_DIR,
        f"requirements_{session_id}.json"
    )

    data["metadata"]["timestamp"] = datetime.utcnow().isoformat()

    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"✅ Requirements file saved at: {file_path}")

    except Exception as e:
        print(f"❌ Failed to write requirements file: {e}")
        raise

    return file_path
