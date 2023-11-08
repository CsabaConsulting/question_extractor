import json
from pathlib import Path

# Define the input and output paths
input_filepath = Path('./data/questions.json')
output_directory = Path('./data/qna')

# Expecting the questions.json with an array of { source, question, answer } pair tuples.
with open(input_filepath, 'r') as input_file:
    input_json = json.load(input_file)
    current_source = None
    current_file = None
    lines = []
    for input_tuple in input_json:
        src = input_tuple["source"]
        if current_source != src:
            if current_file:
                current_file.writelines(lines[:-1])
                current_file.flush()
                current_file.close()

            file_name_stub = src.split("/")[-1].split(".")[0]
            file_path = f"{output_directory}/{file_name_stub}_qna.md"
            current_file = open(file_path, 'w')
            current_source = src
            lines = []
            # with open(src, 'r') as src_file:
            #     src_lines = src_file.readlines()
            #     title = src_lines[0][1:].strip()
            #     lines = [f"# {title} Questions and Answers:\n", "\n"]

        answer = input_tuple['answer'].replace("\n\n", "\n").replace("\n\n", "\n").replace("\n\n", "\n")
        lines.extend([
            f"Question: {input_tuple['question']}\n",
            f"Answer: {answer}\n",
            "---\n"
        ])

    current_file.writelines(lines[:-1])
    current_file.flush()
    current_file.close()
