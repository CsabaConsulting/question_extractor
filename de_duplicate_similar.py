import json
from pathlib import Path

# Define the input file path
input_filepath = Path('./data/questions_dedup.json')
output_filepath = Path('./data/questions_dedup2.json')


with open(input_filepath, "r", encoding="utf-8") as input_file:
    input_json = json.load(input_file)
    output_json = []  # We could get away with the deictionary only, but this way we preserve order
    question_dictionary = dict()
    for qna in input_json:
        if qna["question"] in question_dictionary:
            qna_entry = question_dictionary[qna["question"]]
            if qna["source"] != qna_entry["source"]:
                print(f"Turd in the punch bowl: src1 {qna['source']} vs src2 {qna_entry['source']} q {qna['question']}")
            else:
                print(f"Deduped: q {qna['question']} of src {qna['source']}")
        else:
            question_dictionary[qna["question"]] = dict(source=qna["source"], answer=qna["answer"])
            output_json.append(qna)

    print(f"Dedeup: {len(input_json)} -> {len(question_dictionary)} ({len(output_json)})")
    with open(output_filepath, "w", encoding="utf-8") as output_file:
        json.dump(output_json, output_file, indent=2)
