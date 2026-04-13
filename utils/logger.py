def send_log(logs, message):
    print(f"SENDING: {{'step': 'log', 'message': \"{message}\"}}")
    logs.append(message)


def send_step(step, data=None):
    payload = {"step": step}
    if data:
        payload.update(data)
    print(f"SENDING: {payload}")