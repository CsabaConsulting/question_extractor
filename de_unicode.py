import json
from pathlib import Path
import os
import unicodedata

# Define the input and output paths
data_directory = Path('./data/docs')


def replace_unicode_apostrophes(data):
    return data.replace(u"\u2018\u2018", '"') \
        .replace(u"\u2019\u2019", '"') \
        .replace(u"\u2032\u2032", '"') \
        .replace(u"\u2018", "'") \
        .replace(u"\u2019", "'") \
        .replace(u"\u2032", "'") \
        .replace(u"\u201c", '"') \
        .replace(u"\u201d", '"') \
        .replace("©", 'Copyright') \
        .replace(u"\u00ae", "") \
        .replace(u"\24c7", "") \
        .replace("™", "") \
        .replace(u"\u2122", "") \
        .replace(u"\2120", "") \
        .replace("®", "") \


def unicode_to_ascii(data):
    return unicodedata.normalize("NFKD", data).encode("ascii", "ignore")


def cleanse_off_code_page_characters(file_path):
    """
    Rogue code page characters or MacOS Roman apostrophes, quotation marks,
    dash etc. can be a problem. We recognize these by
    making sure that the preceding and following bytes are ASCII, which
    rules out those cases when these hexa bytes would be part of a UTF-8
    sequence.
    https://en.wikipedia.org/wiki/Mac_OS_Roman

    We'll also treat some Latin1 (Windows CP 1252) characters
    https://www.cl.cam.ac.uk/~mgk25/ucs/quotes.html

    Args:
        file_path: the file's path about to be cleaned
    """

    character_translations = {
        "\xd0": "-",  # Mac OS Roman
        "\xd1": "-",  # Mac OS Roman
        "\xd2": '"',  # Mac OS Roman
        "\xd3": '"',  # Mac OS Roman
        "\xe3": '"',  # Mac OS Roman
        "\xd4": "'",  # Mac OS Roman
        "\xd5": "'",  # Mac OS Roman
        "\xe2": "'",  # Mac OS Roman
        "\x91": "'",  # Latin 1 apostrophe left
        "\x92": "'",  # Latin 1 apostrophe right
        "\x93": '"',  # CE quote left
        "\x94": '"',  # CE quote right
        "\xc1": "'",  # Std grave
        "\xc2": "'",  # Std acute
        "\xa9": "'",  # Std apostrophe
        "\xb4": "'",  # CE acute
        "\xaa": '"',  # Std quote left
        "\xba": '"',  # Std quote right
        "\xea": "'",  # apostrophe from some unknown character set
    }
    chars_to_translate = character_translations.keys()
    modify_count = 0

    with open(file_path, "rb") as input_file:
        file_buffer = input_file.read()
        file_length = len(file_buffer)
        file_pointer = 0
        while file_pointer < file_length:
            byte = file_buffer[file_pointer]

            if byte in chars_to_translate:
                # if the preceding and the following byte is ASCII then
                # we can be sure it's not part of an UTF-8 sequence
                if (
                    not file_pointer or 32 <= file_buffer[file_pointer - 1] <= 127 and
                    file_pointer >= file_length or 32 <= file_buffer[file_pointer + 1] <= 127
                ):
                    # correct the character according to our dictionary
                    file_buffer[file_pointer] = character_translations[byte]
                    modify_count += 1

            file_pointer += 1

    if modify_count > 0:
        with open(file_path, "wb") as output_file:
            output_file.write(file_buffer)

    return modify_count


for root, dirs, files in os.walk(data_directory):
    for file_name in files:
        
        # Check if the file is a markdown file
        if file_name.endswith('.md'):
            file_path = os.path.join(root, file_name)

            # 1. Fix potential off code page characters
            off_cp_modified = cleanse_off_code_page_characters(file_path=file_path)

            # 2. Replace potential unicode apostrophes, quotes, etc.
            unicode_replaced = False
            output_content = ""
            with open(file_path, "r", encoding="utf-8") as input_file:
                input_content = input_file.read()
                output_content = replace_unicode_apostrophes(input_content)
                if input_content != output_content:
                    unicode_replaced = True

            if unicode_replaced:
                with open(file_path, "w") as output_file:
                    output_file.write(output_content)

            unicode_filtered = False
            # 3. Filter any unicode which left
            with open(file_path, "r", encoding="utf-8") as input_file:
                input_content = input_file.read()
                output_content = unicode_to_ascii(input_content)
                if input_content != output_content:
                    unicode_modified = True

            if unicode_filtered:
                with open(file_path, "w") as output_file:
                    output_file.write(output_content)

            if off_cp_modified or unicode_replaced or unicode_filtered:
                print(f"{file_name} modified: {off_cp_modified} off CP chars, unicode replaced {unicode_replaced}, filtered {unicode_filtered}.\n")
