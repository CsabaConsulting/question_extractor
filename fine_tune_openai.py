from pathlib import Path
import os
import openai

# Define the fine tune file path
input_filepath = Path('./data/fine_tune_openai.jsonl')
epochs = 3

openai.api_key = os.getenv('OPENAI_API_KEY')
upload_response = openai.File.create(
  file=open(input_filepath, 'rb'),
  purpose='fine-tune'
)
file_id = upload_response['id']
print(f"Fine tune file {input_filepath} has been uploaded with id {file_id}.\n")

tuning_response = openai.FineTuningJob.create(training_file=file_id, model="gpt-3.5-turbo-1106")
org_id = tuning_response["organization_id"]
tune_model = tuning_response["model"]
tune_id = tuning_response["id"]
print(f"Fine started for {input_filepath} ({file_id}) under org {org_id} with ID {tune_id}.\n")
