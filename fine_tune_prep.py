import json
from pathlib import Path

# Define the input and output paths
input_filepath = Path('./data/questions.json')
output_filepath = Path('./data/fine_tune.jsonl')
system_prompt = \
    "Casey is your assistant specialized in ThruThink budgeting analysis and projection web application usage. " + \
    "It is also knowledgeable in a wide range of budgeting and accounting topics, including EBITDA, " + \
    "cash flow balance, inventory management, and more. While Casey strives to provide accurate information and " + \
    "assistance, please keep in mind that it is not a licensed investment advisor, financial advisor, or tax advisor. " + \
    "Therefore, it cannot provide personalized investment advice, financial planning, or tax guidance. " + \
    "Casey is here to offer general information, answer your questions, and assist with ThruThink-related " + \
    "inquiries to the best of its knowledge."

system_prompt = system_prompt.replace("\n", " ").strip()
# Expecting the questions.json with an array of { source, question, answer } pair tuples.
with open(input_filepath, 'r') as input_file:
    input_json = json.load(input_file)
    # Save the extracted questions as a JSON file
    with open(output_filepath, 'w') as output_file:
        for input_tuple in input_json:
            qna = {
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': input_tuple['question']},
                    {'role': 'assistant', 'content': input_tuple['answer']}
                ]
            }

            json.dump(qna, output_file)
            output_file.write('\n')

        print(f"Results have been saved to {output_filepath}.")
