from pathlib import Path
import os
import openai

# Define the fine tune file path
input_filepath = Path('./data/fine_tune_openai.jsonl')
epochs = 3

# AnyScale uses OpenAI's API
# This code is for Pre 1.0.0 openai PyPi packages (latest is 0.28.1)
openai.api_base = "https://api.endpoints.anyscale.com/v1"
openai.api_key = os.getenv("ANYSCALE_API_KEY") or "ANYSCALE_API_KEY"
upload_response = openai.File.create(
  file=open(input_filepath, 'rb'),
  purpose='fine-tune',
  user_provided_filename='fine_tune_openai.jsonl'
)
file_id = upload_response['id']
print(f"Fine tune file {input_filepath} has been uploaded with id {file_id}.\n")

tuning_response = openai.FineTuningJob.create(training_file=file_id, model="meta-llama/Llama-2-13b-chat-hf")
tune_model = tuning_response["model"]
tune_id = tuning_response["id"]
print(f"Fine started for {input_filepath} ({file_id}) with ID {tune_id}.\n")
