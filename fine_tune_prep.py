import json
from pathlib import Path

# Define the input and output paths
input_filepath = Path('./data/questions.json')
output_filepath = Path('./data/fine_tune_openai.jsonl')
system_prompt = \
    "You are an assistant specialized in ThruThink, which is a budgeting analysis and projection web application. " + \
    "You are also knowledgeable in a wide range of budgeting and accounting topics, including EBITDA, " + \
    "cash flow balance, COGS, inventory management, amortization, and more. " + \
    "Be courteous and go out of your way to help but always be aware of your limitations. " + \
    "While you strives to provide accurate information and assistance, " + \
    "keep in mind that you cannot provide legal personalized investment advice, " + \
    "financial planning, or tax guidance. " + \
    "You are here to offer information about ThruThink usage and details, " + \
    "offer general information about budgeting, answer questions, and assist with " + \
    "ThruThink-related inquiries to the best of your knowledge. " + \
    "If you are uncertain, or cannot find enough information, don't make up anything, " + \
    "but admit that you need more input from the user and you don't have enough information to answer."

system_prompt = system_prompt.replace("\n", " ").strip()
fine_tune_types = ["openai", "azure_openai", "palm2", "anyscale", "cohere"]
fine_tune_type = "anyscale"
if fine_tune_type not in fine_tune_types:
    raise Exception("Invalid fine tune type")

# Expecting the questions.json with an array of { source, question, answer } pair tuples.
with open(input_filepath, 'r') as input_file:
    input_json = json.load(input_file)
    # Save the extracted questions as a JSON file
    with open(output_filepath, 'w') as output_file:
        for input_tuple in input_json:
            qna = {}
            if fine_tune_type in ["openai", "anyscale"]:
                qna = {
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': input_tuple['question']},
                        {'role': 'assistant', 'content': input_tuple['answer']}
                    ]
                }
            elif fine_tune_type in ["azure_openai", "cohere"]:
                qna = {
                    'prompt': input_tuple['question'],
                    'completion': input_tuple['answer']
                }
            elif fine_tune_type == "palm2":
                qna = {
                    'input_text': input_tuple['question'],
                    'output_text': input_tuple['answer']
                }

            json.dump(qna, output_file)
            output_file.write('\n')

        print(f"Results have been saved to {output_filepath}.")
