import json
import os
from pathlib import Path
from dotenv import load_dotenv
from rag_challenge import PDFQuestionAnswerer

# Load environment variables from .env file
load_dotenv()

def main():
    # Get PDF directory from environment variable or use default
    pdf_dir = os.environ.get("PDF_DIR", os.path.expanduser("~/Downloads/pdfs"))
    
    # Create the answerer
    answerer = PDFQuestionAnswerer(
        pdf_dir=pdf_dir,
        pdf_meta_path="pdf-meta.json",
        questions_path="questions.json"
    )
    
    # Test with a single question
    test_question = {
        "text": "Did Liberty Broadband Corporation announce a share buyback plan in the annual report? If there is no mention, return False.",
        "kind": "boolean"
    }
    
    print(f"Testing question: {test_question['text']}")
    
    # Extract company name
    company_name = answerer.extract_company_name(test_question['text'])
    print(f"Extracted company name: {company_name}")
    
    # Find PDF for company
    sha1 = answerer.find_pdf_for_company(company_name)
    print(f"Found PDF with SHA1: {sha1}")
    
    if sha1:
        # Get metadata for company
        meta = answerer.sha1_to_meta.get(sha1, {})
        print(f"Metadata for company: {json.dumps(meta, indent=2)}")
        
        # Process the question
        result = answerer.process_question(test_question)
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Format as final output
        final_output = {"answers": [result]}
        print(f"\nFinal output format: {json.dumps(final_output, indent=2)}")

if __name__ == "__main__":
    main() 