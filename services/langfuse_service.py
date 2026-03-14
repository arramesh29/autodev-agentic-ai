from langfuse import Langfuse

langfuse = Langfuse()

def start_trace(name):
    return langfuse.trace(name=name)
