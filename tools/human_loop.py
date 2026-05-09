def handle_user_input(stage, questions):
    return {
        "step": "user_input_required",
        "stage": stage,
        "questions": questions
    }