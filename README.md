# PDF Question Answering System

This program answers questions about PDF files using metadata and an LLM (Language Model).

## Setup

1. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Set your OpenAI API key as an environment variable:

   ```
   export OPENAI_API_KEY="your-api-key"
   ```

   Alternatively, create a `.env` file based on the provided `.env.example`:

   ```
   cp .env.example .env
   # Edit .env to add your API key
   ```

3. Make sure your PDF files are in the correct location:
   - By default, the program looks for PDFs in `~/Downloads/pdfs`
   - You can specify a different location using the `PDF_DIR` environment variable:
     ```
     export PDF_DIR="/path/to/your/pdfs"
     ```

## Usage

### Basic Usage

Run the program with default settings:

```
python rag_challenge.py
```

### Command-Line Options

The program supports several command-line options:

```
python rag_challenge.py --help
```

Output:

```
usage: rag_challenge.py [-h] [--pdf-dir PDF_DIR] [--pdf-meta PDF_META]
                        [--questions QUESTIONS] [--output OUTPUT]
                        [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                        [--single-question SINGLE_QUESTION]

Answer questions about PDF files using metadata and an LLM.

options:
  -h, --help            show this help message and exit
  --pdf-dir PDF_DIR     Directory containing PDF files (default: ~/Downloads/pdfs)
  --pdf-meta PDF_META   Path to the PDF metadata JSON file (default: pdf-meta.json)
  --questions QUESTIONS
                        Path to the questions JSON file (default: questions.json)
  --output OUTPUT       Path to save the results to (default: answers.json)
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Logging level (default: INFO)
  --single-question SINGLE_QUESTION
                        Process only a single question by index (0-based)
```

### Examples

Process a single question (by index):

```
python rag_challenge.py --single-question 0
```

Use a different PDF directory:

```
python rag_challenge.py --pdf-dir /path/to/pdfs
```

Save results to a different file:

```
python rag_challenge.py --output my_answers.json
```

Increase logging verbosity:

```
python rag_challenge.py --log-level DEBUG
```

## Testing

You can test the functionality with a single question using the provided test script:

```
python test_rag.py
```

## Output Format

The output is a JSON file with the following structure:

```json
{
  "answers": [
    {
      "question_text": "The original question text",
      "value": "The answer to the question",
      "references": [
        {
          "pdf_sha1": "0279901b645e568591ad95dac2c2bf939ef0c00d",
          "page_index": 42
        }
      ]
    },
    {
      "question_text": "Another question",
      "value": "N/A",
      "references": []
    }
  ]
}
```

Where:

- `question_text`: The original question text
- `value`: The answer to the question (or "N/A" if not found)
- `references`: A list of references to where the answer was found
  - `pdf_sha1`: The SHA1 hash of the PDF file
  - `page_index`: The zero-based page index where the answer was found

## Troubleshooting

- If you get an error about the OpenAI API key, make sure you've set the `OPENAI_API_KEY` environment variable correctly.
- If the program can't find your PDF files, make sure they're in the correct location or set the `PDF_DIR` environment variable.
- If you're getting rate limit errors from OpenAI, try increasing the delay between requests by modifying the `time.sleep()` call in the `process_all_questions` method.
