import json
import textwrap
from markdown import Markdown


def cache_text_to_json(text, text_name, json_file):
    """
    Caches a text string by storing it in a JSON file.

    Args:
        text (str): The chat response to be cached.
        text_name (str): The name of the text string to save
        json_file (str): The path to the JSON file where the text string(s) will be stored.

    Returns:
        None
    """
    data = {}
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        pass

    data[text_name] = text

    with open(json_file, 'w') as f:
        json.dump(data, f)


def read_text_from_json(text_name, json_file):
    """
    Reads a specific text from a JSON file.

    Args:
        text_name (str): The name of the text to read from the JSON file.
        json_file (str): The path to the JSON file.

    Returns:
        str: The text corresponding to the given name in the JSON file.
             Returns an empty string if the name is not found.
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    return data.get(text_name, "")


def to_markdown(text):
    """
    Converts plain text to Markdown format.

    Args:
        text (str): The plain text to convert.

    Returns:
        str: The Markdown formatted text.
    """
    text = text.replace('•', '  *')
    #text = text.replace('\n\n', '\n')
    return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))
