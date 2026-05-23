import json
import os

TRACE_FILE = "rag_data/traceability.json"


def load_trace():

    if os.path.exists(TRACE_FILE):
        with open(TRACE_FILE, "r") as f:
            return json.load(f)

    return []


def save_trace(data):

    with open(TRACE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_requirement_trace(req):

    trace = load_trace()

    trace.append({
        "req_id": req.get("id"),
        "description": req.get("description"),
        "source": req.get("source"),
        "code_files": [],
        "test_files": []
    })

    save_trace(trace)


def link_code(req_id, filename):

    trace = load_trace()

    for t in trace:

        if t["req_id"] == req_id:
            t["code_files"].append(filename)

    save_trace(trace)


def link_test(req_id, filename):

    trace = load_trace()

    for t in trace:

        if t["req_id"] == req_id:
            t["test_files"].append(filename)

    save_trace(trace)