import json

DATA_PATH = "./data/fine_tune_openai.jsonl"

# Load the dataset
with open(DATA_PATH, 'r', encoding='utf-8') as f:
    items = [json.loads(line) for line in f]

class DataFormatError(Exception):
    pass

def check_data_for_format_errors(items: list):

    for line_num, batch in enumerate(items):
        prefix = f"Error in line #{line_num + 1}: "
        if not isinstance(batch, dict):
            raise DataFormatError(
                f"{prefix}Each line in the provided data should be a dictionary"
            )

        if "messages" not in batch:
            raise DataFormatError(
                f"{prefix}Each line in the provided data should have a 'messages' key"
            )

        if not isinstance(batch["messages"], list):
            raise DataFormatError(
                f"{prefix}Each line in the provided data should have a 'messages' key with a list of messages"
            )

        messages = batch["messages"]
        if not any(message.get("role", None) == "assistant" for message in messages):
            raise DataFormatError(
                f"{prefix}Each message list should have at least one message with role 'assistant'"
            )

        for message_num, message in enumerate(messages):
            prefix = f"Error in line #{line_num + 1}, message #{message_num + 1}: "
            if "role" not in message or "content" not in message:
                raise DataFormatError(
                    f"{prefix}Each message should have a 'role' and 'content' key"
                )

            if any(k not in ("role", "content", "name") for k in message):
                raise DataFormatError(
                    f"{prefix}Each message should only have 'role', 'content', and 'name' keys, any other key is not allowed"
                )

            if message.get("role", None) not in ("system", "user", "assistant"):
                raise DataFormatError(
                    f"{prefix}Each message should have a valid role (system, user, or assistant)"
                )


try:
    check_data_for_format_errors(items)
    print("Data format is valid!")
except DataFormatError as e:
    print("Data format is NOT valid!")
    print(e)
