import json
import re
import os
import asyncio
import openai
from pathlib import Path
from tenacity import (
    retry,
    wait_random_exponential,
)
import openai.error
# from aiolimiter import AsyncLimiter
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
# Trying to avoid similar questions
import textdistance
# from contextlib import asynccontextmanager
from .markdown import load_markdown_files_from_directory, split_markdown
from .token_counting import count_tokens_text, count_tokens_messages, get_available_tokens, are_tokens_available_for_both_conversations
from .prompts import create_answering_conversation_messages, create_extraction_conversation_messages

# replace the "Key" with your own API key
API_KEY = os.getenv("OPENAI_API_KEY") or "OPENAI_API_KEY"
#---------------------------------------------------------------------------------------------
# QUESTION PROCESSING

# Ensure we do not run too many concurent requests
model_rate_limits = 2000
max_concurent_request = int(model_rate_limits * 0.75)
throttler = asyncio.Semaphore(max_concurent_request)
jaro_winkler = textdistance.JaroWinkler()
similarity_thrashold = 0.9
edit_disance = textdistance.Levenshtein()
distance_thrashold = 6
distance_ratio = 0.25
question_dict = dict()
question_list = list()
question_similarity_lookback = 200

def flatten_nested_lists(nested_lists):
    """
    Takes a list of lists as input and returns a flattened list containing all elements.
    
    Args:
        nested_lists (list of lists): A list containing one or more sublists.

    Returns:
        list: A flattened list containing all elements from the input nested lists.
    """
    flattened_list = []

    # Iterate through the nested lists and add each element to the flattened_list
    for sublist in nested_lists:
        flattened_list.extend(sublist)

    return flattened_list

@retry(
    wait=wait_random_exponential(min=15, max=40),
    # sleep=1,
)
async def run_model(messages):
    """
    Asynchronously runs the chat model with as many tokens as possible on the given messages.
    
    Args:
        messages (list): A list of input messages to be processed by the model.

    Returns:
        str: The model-generated output text after processing the input messages.
    """
    # Count the number of tokens in the input messages
    num_tokens_in_messages = count_tokens_messages(messages)

    # Calculate the number of tokens available for processing
    num_tokens_available = get_available_tokens(num_tokens_in_messages)

    # Create an instance of the ChatOpenAI model with minimum imagination (temperature set to 0)
    model = ChatOpenAI(temperature=0.0, max_tokens=num_tokens_available)

    try:
        # Use a semaphore to limit the number of simultaneous calls
        async with throttler:
            # Asynchronously run the model on the input messages
            output = await model._agenerate(messages)
    except openai.error.RateLimitError as e:
        print(f"ERROR ({e}): Rate limit exceeded, retrying.")
        await asyncio.sleep(1)
        raise  # Re-raise the exception to allow tenacity to handle the retry
    except openai.error.APIConnectionError as e:
        print(f"ERROR ({e}): Could not connect, retrying.")
        await asyncio.sleep(1)
        raise  # Re-raise the exception to allow tenacity to handle the retry
    except Exception as e:
        print(f"ERROR ({e}): Could not generate text for an input.")
        return 'ERROR'
    
    # Extract and return the generated text from the model output
    return output.generations[0].text.strip()

def extract_questions_from_output(output):
    """
    Takes a numbered list of questions as a string and returns them as a list of strings.
    The input might have prefixes/suffixes that are not questions or incomplete questions.

    Args:
        output (str): A string containing a numbered list of questions.

    Returns:
        list of str: A list of extracted questions as strings.
    """
    # Define a regex pattern to match questions (lines starting with a number followed by a dot and a space)
    question_pattern = re.compile(r"^\s*\d+\.\s*(.+)$", re.MULTILINE)

    # Find all the questions matching the pattern in the input text
    questions = question_pattern.findall(output)

    # Check if the last question is incomplete (does not end with punctuation or a parenthesis)
    if (len(questions) > 0) and (not re.search(r"[.!?)]$", questions[-1].strip())):
        print(f"WARNING: Popping incomplete question: '{questions[-1]}'")
        questions.pop()

    return questions


async def extract_questions_from_text(file_path, text, parallel=True):
    """
    Asynchronously extracts questions from the given text.
    
    Args:
        file_path (str): The file path of the markdown file.
        text (str): The text content of the markdown file.

    Returns:
        list of tuple: A list of tuples, each containing the file path, text, and extracted question.
    """
    # Ensure the text can be processed by the model
    text = text.strip()
    num_tokens_text = count_tokens_text(text)

    if not are_tokens_available_for_both_conversations(num_tokens_text):
        # Split text and call function recursively
        print(f"WARNING: Splitting '{file_path}' into smaller chunks.")

        # Build tasks for each subsection of the text
        tasks = []
        task_outputs = []
        for sub_title, sub_text in split_markdown(text):
            sub_file_path = file_path + '/' + sub_title.replace('# ', '#').replace(' ', '-').lower()
            task = extract_questions_from_text(sub_file_path, sub_text)
            if parallel:
                tasks.append(task)
            else:
                task_output = await task
                task_outputs.append(task_output)

        if parallel:
            # Asynchronously run tasks and gather outputs
            tasks_outputs = await asyncio.gather(*tasks)

        # Flatten and return the results
        return flatten_nested_lists(tasks_outputs)
    else:
        # The first split is the whole
        all_splits = [Document(page_content=text)]

        # Then we chunk up the rest (in an intelligent way context aware)
        # https://python.langchain.com/docs/use_cases/question_answering/how_to/document-context-aware-QA
        headers_to_split_on = [
            # ("#", "Title"),
            # ("##", "Category"),
            ("###", "Section"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        md_header_splits = markdown_splitter.split_text(text)

        chunk_size = 500
        chunk_overlap = 150
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        all_splits.extend(text_splitter.split_documents(md_header_splits))

        lines = text.split("\n")
        title = lines[0]
        category = lines[1]
        prepend = "\n".join([title, category, ""])
        outputs = []
        for split in all_splits:
            text_chunk = split.page_content
            if not text_chunk.startswith(prepend):
                text_chunk = prepend + text_chunk

            # Run the model to extract questions
            messages = create_extraction_conversation_messages(text_chunk)
            output = await run_model(messages)
            questions = extract_questions_from_output(output)

            # Associate questions with source information and return as a list of tuples
            for question in questions:
                question = question.strip()
                if question in question_dict:
                    continue
                else:
                    question_dict[question] = True

                similar = False
                for q in question_list[-question_similarity_lookback:]:
                    similarity = jaro_winkler(question, q)
                    distance = edit_disance(question, q)
                    if (
                        similarity > similarity_thrashold and
                        (distance < distance_thrashold or distance < max(len(question), len(q)) * distance_ratio)
                    ):
                        similar = True
                        break

                if similar:
                    continue
                else:
                    question_list.append(question)

                outputs.append((file_path, text_chunk, question))

        return outputs


async def generate_answer(question, source):
    """
    Asynchronously generates an answer to a given question using the provided source text.
    
    Args:
        question (str): The question to be answered.
        source (str): The text containing relevant information for answering the question.

    Returns:
        str: The generated answer to the question.
    """
    # Create the input messages for the chat model
    messages = create_answering_conversation_messages(question, source)
    # Asynchronously run the chat model with the input messages
    answer = await run_model(messages)

    return answer

#---------------------------------------------------------------------------------------------
# FILE PROCESSING

async def process_file(file_path, text, progress_counter, verbose=True, parallel=True, max_qa_pairs=300):
    """
    Asynchronously processes a file, extracting questions and generating answers concurrently.
    
    Args:
        file_path (str): The file path of the markdown file.
        text (str): The text content of the markdown file.
        progress_counter (dict): A dictionary containing progress information ('nb_files_done' and 'nb_files').
        verbose (bool): If True, print progress information. Default is True.

    Returns:
        list: A list of dictionaries containing source, question, and answer information.
    """
    questions_file_name = f"{file_path}.json"
    if Path(questions_file_name).is_file():
        with open(questions_file_name, 'r') as input_file:
            questions = json.loads(input_file.read())
    else:
        # Extract questions from the text
        questions = await extract_questions_from_text(file_path, text, parallel=parallel)

        # Limit the number of questions processed
        if max_qa_pairs > 0:
            questions = questions[:max_qa_pairs]

        with open(questions_file_name, 'w') as output_file:
            json.dump(questions, output_file, indent=2)

    results_filename = f"{file_path}_result.json"
    result = []
    if Path(results_filename).is_file():
        with open(results_filename, 'r') as input_file2:
            result = json.loads(input_file2.read())
    else:
        # Build and run answering tasks concurrently
        tasks = []
        for sub_file_path, sub_text, question in questions:
            task = generate_answer(question, sub_text)
            tasks.append(task)

        tasks_outputs = await asyncio.gather(*tasks)

        # Merge results into a list of dictionaries
        for (sub_file_path, sub_text, question), answer in zip(questions, tasks_outputs):
            result.append({'source': sub_file_path, 'question': question, 'answer': answer})

        with open(results_filename, 'w') as output_file2:
            json.dump(questions, output_file2, indent=2)

    # Update progress and display information if verbose is True
    progress_counter['nb_files_done'] += 1  # No race condition as we are single-threaded
    if verbose:
        print(f"{progress_counter['nb_files_done']}/{progress_counter['nb_files']}: File '{file_path}' done!")

    return result


async def process_files(files, verbose=True, parallel=True, max_qa_pairs=300):
    """
    Asynchronously processes a list of files, extracting questions and generating answers concurrently.
    
    Args:
        files (list): A list of tuples containing file paths and their respective text content.
        verbose (bool): If True, print progress information. Default is True.

    Returns:
        list: A merged list of dictionaries containing source, question, and answer information.
    """
    # Set up progress information for display
    nb_files = len(files)
    progress_counter = {'nb_files': nb_files, 'nb_files_done': 0}
    if verbose: print(f"Starting question extraction on {nb_files} files.")

    # Build and run tasks for each file concurrently
    tasks = []
    tasks_outputs = []
    for file_path, text in files:
        task = process_file(file_path, text, progress_counter, verbose=verbose, max_qa_pairs=max_qa_pairs)
        if parallel:
            tasks.append(task)
        else:
            tasks_output = await task
            tasks_outputs.append(tasks_output)
            await asyncio.sleep(0.005)

    if parallel:
        tasks_outputs = await asyncio.gather(*tasks)

    # Merge results from all tasks
    return flatten_nested_lists(tasks_outputs)

#---------------------------------------------------------------------------------------------
# MAIN

def extract_questions_from_directory(input_folder, verbose=True, parallel=True, max_qa_pairs=300):
    """
    Extracts questions and answers from all markdown files in the input folder.

    Args:
        input_folder (str): A path to a folder containing markdown files.
        verbose (bool): If True, print progress information. Default is True.

    Returns:
        list: A list of dictionaries containing path, source, question, and answer information.
    """
    # Load input files from the folder
    if verbose: print(f"Loading files from '{input_folder}'.")
    files = load_markdown_files_from_directory(input_folder)

    # Run question extraction tasks
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(process_files(files, verbose=verbose, parallel=parallel, max_qa_pairs=max_qa_pairs))

    if verbose: print(f"Done, {len(results)} question/answer pairs have been generated!")
    return results
