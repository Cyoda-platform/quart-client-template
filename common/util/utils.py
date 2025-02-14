import logging
import queue
import time
import re

import aiofiles
from typing import Optional, Any
import uuid
import json

import aiohttp
import jsonschema
from jsonschema import validate

from common.config.config import PROJECT_DIR, REPOSITORY_NAME

logger = logging.getLogger(__name__)

class ValidationErrorException(Exception):
    """Custom exception for validation errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def get_user_history_answer(response):
    answer = response.get('message', '') if response and isinstance(response, dict) else ''
    if isinstance(answer, dict) or isinstance(answer, list):
        answer = json.dumps(answer)
    return answer


def generate_uuid() -> uuid:
    return uuid.uuid1()


def _normalize_boolean_json(json_data):
    if isinstance(json_data, dict):
        for key, value in json_data.items():
            if isinstance(value, str):
                if (value in ["'true'", "'True'", 'True', "true", "True"]):
                    json_data[key] = True
                elif (value in ["'false'", "'False'", 'False', "false", "False"]):
                    json_data[key] = False
            elif isinstance(value, dict):
                json_data[key] = _normalize_boolean_json(value)
    return json_data


def remove_js_style_comments_outside_strings(code: str) -> str:
    """
    Remove //... comments ONLY if they appear outside of a quoted string.

    This prevents 'https://...' in a JSON string from being mistaken as a comment.
    """

    result = []
    in_string = False
    escape_char = False
    i = 0
    length = len(code)

    while i < length:
        char = code[i]

        # Check for string toggle (double quotes only for JSON)
        if char == '"' and not escape_char:
            # Toggle string on/off
            in_string = not in_string
            result.append(char)
        elif not in_string:
            # We are outside a string, so check if we have //
            if char == '/' and i + 1 < length and code[i + 1] == '/':
                # Skip rest of the line
                # Move i to the next newline or end of text
                i += 2
                while i < length and code[i] not in ('\n', '\r'):
                    i += 1
                # Do NOT append the '//...' to result
                # We effectively remove it
                continue
            else:
                # Normal character outside string
                result.append(char)
        else:
            # Inside a string
            result.append(char)

        # Handle escape chars inside strings
        if char == '\\' and in_string and not escape_char:
            # Next character is escaped
            escape_char = True
        else:
            escape_char = False

        i += 1

    return ''.join(result)


def parse_json(text: str) -> str:
    """
    1. Find the first occurrence of '{' or '[' and the matching last occurrence
       of '}' or ']', respectively (very naive bracket slicing).
    2. Remove only real JS-style comments (// ...) outside of strings.
    3. Attempt to parse the substring as JSON.
    4. Return prettified JSON if successful, otherwise the original text.
    """

    original_text = text
    text = text.strip()

    # Find earliest occurrences
    first_curly = text.find('{')
    first_square = text.find('[')

    if first_curly == -1 and first_square == -1:
        # No bracket found
        return original_text

    # Decide which bracket to use based on which occurs first
    if first_curly == -1:
        start_index = first_square
        close_bracket = ']'
    elif first_square == -1:
        start_index = first_curly
        close_bracket = '}'
    else:
        if first_curly < first_square:
            start_index = first_curly
            close_bracket = '}'
        else:
            start_index = first_square
            close_bracket = ']'

    # Find the last occurrence of that bracket
    end_index = text.rfind(close_bracket)
    if end_index == -1 or end_index < start_index:
        return original_text

    # Extract the substring
    json_substring = text[start_index:end_index + 1]

    # Remove only actual JS-style comments outside strings
    json_substring = remove_js_style_comments_outside_strings(json_substring)

    # Attempt to parse the cleaned substring
    try:
        parsed = json.loads(json_substring)
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        # If it fails, just return the original
        return original_text

def parse_workflow_json(result: str) -> str:
    # Function to replace single quotes with double quotes and handle True/False
    def convert_to_json_compliant_string(text: str) -> str:
        # Convert Python-style booleans to JSON booleans (True -> true, False -> false)
        text = text.replace("True", "true").replace("False", "false")

        # Replace single quotes with double quotes for strings
        # This replacement will happen only for string-like values (inside curly braces or key-value pairs)
        text = re.sub(r"(?<=:)\s*'(.*?)'\s*(?=\s*,|\s*\})", r'"\1"', text)  # For values
        text = re.sub(r"(?<=,|\{|\[)\s*'(.*?)'\s*(?=\s*:|\s*,|\s*\])", r'"\1"', text)  # For keys

        # Ensure the surrounding quotes around strings
        text = re.sub(r"(?<=:)\s*'(.*?)'\s*(?=\s*,|\s*\})", r'"\1"', text)
        return text

    # If result is a dictionary, convert it to JSON with double quotes
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False)

    # If result is a string, process it for improper quote handling
    if isinstance(result, str):
        if result.startswith("```json"):
            # Extract the content inside the json code block
            start_index = result.find("```json") + len("```json\n")
            end_index = result.find("```", start_index)
            json_content = result[start_index:end_index].strip()

            # Apply the corrections: Convert single quotes, True/False to JSON-compatible format
            json_content = convert_to_json_compliant_string(json_content)

            # Try to parse the extracted content as JSON
            try:
                parsed_json = json.loads(json_content)
                return json.dumps(parsed_json, ensure_ascii=False)
            except json.JSONDecodeError:
                return json_content  # If parsing fails, return the original content as is
        elif result.startswith("```"):
            # If result is a general code block, strip the backticks and return it
            return "\n".join(result.split("\n")[1:-1])
        else:
            # Apply the corrections to the string content
            result = convert_to_json_compliant_string(result)
            return result

    # Return result as-is if it's neither a dictionary nor a valid string format
    return result


def main():
    # Example input
    input_data = """
Here is an example JSON data structure for the entity `data_analysis_job`, reflecting the business app_init based on the user's requirement to analyze London Houses data using pandas:

```json
{
  "job_id": "data_analysis_job_001",
  "job_name": "Analyze London Houses Data",
  "job_status": "completed",
  "start_time": "2023-10-01T10:05:00Z",
  "end_time": "2023-10-01T10:30:00Z",
  "input_data": {
    "raw_data_entity_id": "raw_data_entity_001",
    "data_source": "https://raw.githubusercontent.com/Cyoda-platform/cyoda-ai/refs/heads/ai-2.x/data/test-inputs/v1/connections/london_houses.csv"
  },
  "analysis_parameters": {
    "metrics": [
      {
        "name": "average_price",
        "description": "Calculate the average price of the houses.",
        "value": 1371200
      },
      {
        "name": "median_square_meters",
        "description": "Find the median square meters of the houses.",
        "value": 168
      }
    ],
    "filters": {
      "neighborhood": ["Notting Hill", "Westminster"],
      "min_bedrooms": 2,
      "max_bathrooms": 3
    }
  },
  "analysis_results": {
    "total_houses_analyzed": 3,
    "houses_with_garden": 2,
    "houses_with_parking": 1,
    "price_distribution": {
      "min_price": 1476000,
      "max_price": 2291200,
      "average_price": 1371200
    },
    "visualizations": [
      {
        "type": "bar_chart",
        "title": "Price Distribution by Neighborhood",
        "data": [
          {
            "neighborhood": "Notting Hill",
            "count": 1,
            "average_price": 2291200
          },
          {
            "neighborhood": "Westminster",
            "count": 1,
            "average_price": 1476000
          },
          {
            "neighborhood": "Soho",
            "count": 1,
            "average_price": 1881600
          }
        ]
      },
      {
        "type": "scatter_plot",
        "title": "Square Meters vs Price",
        "data": [
          {
            "square_meters": 179,
            "price": 2291200
          },
          {
            "square_meters": 123,
            "price": 1476000
          },
          {
            "square_meters": 168,
            "price": 1881600
          }
        ]
      }
    ]
  },
  "report_output": {
    "report_id": "report_001",
    "report_format": "PDF",
    "generated_at": "2023-10-01T10:35:00Z",
    "report_link": "https://example.com/reports/report_001.pdf"
  }
}
```

### Explanation
- **job_id, job_name, job_status**: Basic identifiers and status of the analysis job.
- **input_data**: Contains references to the raw data entity that is being analyzed and where the data is sourced from.
- **analysis_parameters**: Specifies the metrics to be calculated and any filters applied during the analysis.
- **analysis_results**: Summarizes the outcomes of the data analysis, including total houses analyzed, distribution of prices, and visual representations of the results.
- **report_output**: Information about the generated report, including its format, generation time, and a link to access it. 

This JSON structure provides a comprehensive overview of the analysis conducted on the London Houses data, reflecting the required business app_init for the `data_analysis_job` entity.   """
    output_data = parse_json(input_data)

    print(output_data)

if __name__ == "__main__":
    main()

async def validate_result(data: str, file_path: str, schema: Optional[str]) -> str:
    if file_path:
        try:
            async with aiofiles.open(file_path, "r") as schema_file:
                content = await schema_file.read()
                schema = json.load(content)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error reading schema file {file_path}: {e}")
            raise

    try:
        parsed_data = parse_json(data)
        json_data = json.loads(parsed_data)
        normalized_json_data = _normalize_boolean_json(json_data)
        validate(instance=normalized_json_data, schema=schema)
        logger.info("JSON validation successful.")
        return normalized_json_data
    except jsonschema.exceptions.ValidationError as err:
        logger.error(f"JSON schema validation failed: {err.message}")
        raise ValidationErrorException(message = f"JSON schema validation failed: {err}, {err.message}")
    except json.JSONDecodeError as err:
        logger.error(f"Failed to decode JSON: {err}")
        try:
            parsed_data = parse_json(data)
            errors = consolidate_json_errors(parsed_data)
        except Exception as e:
            logger.error(f"Failed to consolidate JSON errors: {e}")
            errors = [str(e)]
        raise ValidationErrorException(message = f"Failed to decode JSON: {err}, {err.msg}, {errors} . Please make sure the json returned is correct and aligns with json formatting rules. make sure you're using quotes for string values, including None")
    except Exception as err:
        logger.error(f"Unexpected error during JSON validation: {err}")
        raise ValidationErrorException(message = f"Unexpected error during JSON validation: {err}")


def consolidate_json_errors(json_str):
    errors = []

    # Try to parse the JSON string
    try:
        json_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        errors.append(f"JSONDecodeError: {e}")

        # Extract the problematic part of the JSON string
        error_pos = e.pos
        error_line = json_str.count('\n', 0, error_pos) + 1
        error_col = error_pos - json_str.rfind('\n', 0, error_pos)

        errors.append(f"Error at line {error_line}, column {error_col}")

        # Try to find the context around the error
        context_start = max(0, error_pos - 20)
        context_end = min(len(json_str), error_pos + 20)
        context = json_str[context_start:context_end]
        errors.append(f"Context around error: {context}")

        # Attempt to fix common JSON issues
        # Example: Fixing unescaped quotes
        fixed_json_str = re.sub(r'(?<!\\)"', r'\"', json_str)

        try:
            json_data = json.loads(fixed_json_str)
            errors.append("JSON was successfully parsed after fixing unescaped quotes.")
        except json.JSONDecodeError as e:
            errors.append("Failed to fix JSON after attempting to fix unescaped quotes.")

    return errors



async def read_file(file_path: str):
    """Read and return JSON entity from a file."""
    try:
        async with aiofiles.open(file_path, 'r') as file:
            content = await file.read()
            return content
    except Exception as e:
        logger.error(f"Failed to read JSON file {file_path}: {e}")
        raise  # Re-raise the exception for further handling


async def read_json_file(file_path: str):
    try:
        async with aiofiles.open(file_path, "r") as file:
            content = await file.read()  # Read the file content asynchronously
            data = json.loads(content)  # Parse the content as JSON
        logger.info(f"Successfully read JSON file: {file_path}")
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding failed for file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading the file {file_path}: {e}")
        raise

async def send_get_request(token: str, api_url: str, path: str) -> Optional[Any]:
    url = f"{api_url}/{path}"
    token = f"Bearer {token}" if not token.startswith('Bearer') else token
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"{token}",
    }
    try:
        response = await send_request(headers, url, 'GET', None, None)
        # Raise an error for bad status codes
        logger.info(f"GET request to {url} successful.")
        return response
    except Exception as err:
        logger.error(f"Error during GET request to {url}: {err}")
        raise


async def send_request(headers, url, method, data, json):
    async with aiohttp.ClientSession() as session:
        if method == 'GET':
            async with session.get(url, headers=headers) as response:
                if response and (response.status == 200 or response.status == 404):
                    response_data = {"status": response.status,
                                     "json": await response.json() if response.content_type == 'application/json' else await response.text()}
        elif method == 'POST':
            async with session.post(url, headers=headers, data=data, json=json) as response:
                if response:
                    response_data = {"status": response.status,
                                     "json": await response.json() if response.content_type == 'application/json' else await response.text()}
        elif method == 'PUT':
            async with session.put(url, headers=headers, data=data, json=json) as response:
                if response:
                    response_data = {"status": response.status,
                                     "json": await response.json() if response.content_type == 'application/json' else await response.text()}
        elif method == 'DELETE':
            async with session.delete(url, headers=headers) as response:
                if response:
                    response_data = {"status": response.status,
                                     "json": await response.json() if response.content_type == 'application/json' else await response.text()}
    return response_data


async def send_post_request(token: str, api_url: str, path: str, data=None, json=None) -> Optional[Any]:
    url = f"{api_url}/{path}"
    token = f"Bearer {token}" if not token.startswith('Bearer') else token
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"{token}",
    }
    try:
        response = await send_request(headers, url, 'POST', data, json)
        return response
    except Exception as err:
        logger.error(f"Error during POST request to {url}: {err}")
        raise


async def send_put_request(token: str, api_url: str, path: str, data=None, json=None) -> Optional[Any]:
    url = f"{api_url}/{path}"
    token = f"Bearer {token}" if not token.startswith('Bearer') else token
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"{token}",
    }
    try:
        response = await send_request(headers, url, 'PUT', data, json)
        logger.info(f"PUT request to {url} successful.")
        return response
    except Exception as err:
        logger.error(f"Error during PUT request to {url}: {err}")
        raise


async def send_delete_request(token: str, api_url: str, path: str) -> Optional[Any]:
    url = f"{api_url}/{path}"
    token = f"Bearer {token}" if not token.startswith('Bearer') else token
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"{token}",
    }
    try:
        response = await send_request(headers, url, 'DELETE', None, None)
        logger.info(f"GET request to {url} successful.")
        return response
    except Exception as err:
        logger.error(f"Error during GET request to {url}: {err}")
        raise


def expiration_date(seconds: int) -> int:
    return int((time.time() + seconds) * 1000.0)


def now():
    timestamp = int(time.time() * 1000.0)
    return timestamp


def timestamp_before(seconds: int) -> int:
    return int((time.time() - seconds) * 1000.0)

def clean_formatting(text):
    """
    Convert multi-line text into a single line, preserving all other content.
    """
    # Replace any sequence of newlines (and carriage returns) with a single space
    return re.sub(r'[\r\n]+', ' ', text)
# def clean_formatting(text):
#     """
#     This function simulates the behavior of text pasted into Google search:
#     - Removes leading and trailing whitespace.
#     - Condenses multiple spaces into a single space.
#     - Keeps alphanumeric characters and spaces only, removing other characters.
#
#     :param answer: The input string to be cleaned
#     :return: A cleaned string
#     """
#     # Remove leading and trailing whitespace
#     text = text.strip()
#
#     # Condense multiple spaces into a single space
#     text = re.sub(r'\s+', ' ', text)
#
#     # Remove non-alphanumeric characters (excluding spaces)
#     text = re.sub(r'[^\w\s]', '', text)
#
#     return text


def get_project_file_name(chat_id, file_name):
    return f"{PROJECT_DIR}/{chat_id}/{REPOSITORY_NAME}/{file_name}"


def custom_serializer(obj):
    if isinstance(obj, queue.Queue):
        # Convert queue to list
        return list(obj.queue)
    raise TypeError(f"Type {type(obj)} not serializable")


def format_json_if_needed(data, key):
    value = data.get(key)
    if isinstance(value, dict):
        # Pretty print the JSON object
        formatted_json = json.dumps(value, indent=4)
        data[key] = f"```json \n{formatted_json}\n```"
    else:
        print(f"Data at {key} is not a valid JSON object: {value}")  # Optionally log this or handle it
    return data