import json
import os
import re
import argparse
from pathlib import Path
import PyPDF2
from openai import OpenAI
from typing import Dict, List, Any, Tuple, Optional
import logging
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
if not os.environ.get("OPENAI_API_KEY"):
    logger.warning("OPENAI_API_KEY not found in environment variables. Please set it before running the program.")

class PDFQuestionAnswerer:
    def __init__(self, pdf_dir: str, pdf_meta_path: str, questions_path: str):
        """
        Initialize the PDF Question Answerer.
        
        Args:
            pdf_dir: Directory containing PDF files
            pdf_meta_path: Path to the PDF metadata JSON file
            questions_path: Path to the questions JSON file
        """
        self.pdf_dir = Path(pdf_dir)
        self.pdf_meta_path = Path(pdf_meta_path)
        self.questions_path = Path(questions_path)
        self.pdf_meta = self._load_json(self.pdf_meta_path)
        self.questions = self._load_json(self.questions_path)
        
        # Create a mapping from company name to SHA1 for quick lookup
        self.company_to_sha1 = {
            meta["company_name"].lower(): meta["sha1"] 
            for meta in self.pdf_meta
        }
        
        # Create a mapping from SHA1 to metadata for quick lookup
        self.sha1_to_meta = {
            meta["sha1"]: meta 
            for meta in self.pdf_meta
        }
        
    def _load_json(self, path: Path) -> List[Dict[str, Any]]:
        """Load and parse a JSON file."""
        with open(path, 'r') as f:
            return json.load(f)
    
    def extract_company_name(self, question: str) -> Optional[str]:
        """
        Extract the company name from a question.
        
        Args:
            question: The question text
            
        Returns:
            The company name if found, None otherwise
        """
        # Look for patterns like "For [Company], what was..." or "[Company] announced..."
        patterns = [
            r"For\s+([^,\.]+?),",  # "For Company, what..."
            r"Did\s+([^,\.]+?)\s+announce",  # "Did Company announce..."
            r"by\s+([^,\.]+?)\s+according",  # "by Company according..."
            r"at\s+([^,\.]+?)\s+in",  # "at Company in..."
            r"What\s+is\s+the\s+([^,\.]+?)'s",  # "What is the Company's..."
        ]
        
        for pattern in patterns:
            match = re.search(pattern, question)
            if match:
                return match.group(1).strip()
        
        # If no pattern matches, use LLM to extract company name
        return self._extract_company_name_with_llm(question)
    
    def _extract_company_name_with_llm(self, question: str) -> Optional[str]:
        """Use LLM to extract company name from question."""
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract only the company name from the following question. Return just the company name, nothing else."},
                    {"role": "user", "content": question}
                ],
                temperature=0,
                max_tokens=50
            )
            company_name = response.choices[0].message.content.strip()
            return company_name
        except Exception as e:
            logger.error(f"Error extracting company name with LLM: {e}")
            return None
    
    def find_pdf_for_company(self, company_name: str) -> Optional[str]:
        """
        Find the PDF file for a given company name.
        
        Args:
            company_name: The company name to search for
            
        Returns:
            The SHA1 of the PDF file if found, None otherwise
        """
        # Try exact match first
        company_lower = company_name.lower()
        if company_lower in self.company_to_sha1:
            return self.company_to_sha1[company_lower]
        
        # Try fuzzy matching
        best_match = None
        best_score = 0
        
        for comp_name, sha1 in self.company_to_sha1.items():
            # Simple word overlap score
            words1 = set(company_lower.split())
            words2 = set(comp_name.split())
            overlap = len(words1.intersection(words2))
            
            if overlap > best_score:
                best_score = overlap
                best_match = sha1
        
        # Only return if we have a reasonable match
        if best_score > 0:
            return best_match
        
        return None
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[str]:
        """
        Extract text from a PDF file, page by page.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of strings, one per page
        """
        pages = []
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    pages.append(page.extract_text())
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
        
        return pages
    
    def answer_question_with_llm(self, question: str, context: str, kind: str) -> Tuple[str, float]:
        """
        Use LLM to answer a question based on the provided context.
        
        Args:
            question: The question to answer
            context: The context to use for answering
            kind: The kind of answer expected (number, boolean, names, etc.)
            
        Returns:
            The answer and a confidence score
        """
        try:
            prompt = f"""
            Answer the following question based ONLY on the provided context.
            
            Context:
            {context}
            
            Question: {question}
            
            The answer should be a {kind}. If the information is not available in the context, return 'N/A'.
            
            Answer:
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based only on the provided context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=100
            )
            
            answer = response.choices[0].message.content.strip()
            confidence = 0.9  # Placeholder for confidence score
            
            return answer, confidence
        except Exception as e:
            logger.error(f"Error answering question with LLM: {e}")
            return "N/A", 0.0
    
    def process_question(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single question and return the answer.
        
        Args:
            question_data: The question data
            
        Returns:
            A dictionary with the question_text, value, and references
        """
        question_text = question_data["text"]
        kind = question_data["kind"]
        
        # Extract company name from question
        company_name = self.extract_company_name(question_text)
        if not company_name:
            logger.warning(f"Could not extract company name from question: {question_text}")
            return {"question_text": question_text, "value": "N/A", "references": []}
        
        # Find PDF for company
        sha1 = self.find_pdf_for_company(company_name)
        if not sha1:
            logger.warning(f"Could not find PDF for company: {company_name}")
            return {"question_text": question_text, "value": "N/A", "references": []}
        
        # Construct PDF path
        pdf_path = self.pdf_dir / f"{sha1}.pdf"
        if not pdf_path.exists():
            logger.warning(f"PDF file not found: {pdf_path}")
            return {"question_text": question_text, "value": "N/A", "references": []}
        
        # Extract text from PDF
        pages = self.extract_text_from_pdf(str(pdf_path))
        if not pages:
            logger.warning(f"Could not extract text from PDF: {pdf_path}")
            return {"question_text": question_text, "value": "N/A", "references": []}
        
        # Use metadata to narrow down search if possible
        meta = self.sha1_to_meta.get(sha1, {})
        
        # Check if we can use metadata to determine the answer directly
        # For example, if the question is about share buybacks and the metadata says there are none
        if "share buyback" in question_text.lower() and not meta.get("has_share_buyback_plans", False):
            if kind == "boolean" and "did" in question_text.lower():
                return {"question_text": question_text, "value": "False", "references": [{"pdf_sha1": sha1, "page_index": 0}]}
        
        if "dividend policy" in question_text.lower() and not meta.get("has_dividend_policy_changes", False):
            if kind == "boolean" and "did" in question_text.lower():
                return {"question_text": question_text, "value": "False", "references": [{"pdf_sha1": sha1, "page_index": 0}]}
        
        if "mergers" in question_text.lower() and not meta.get("mentions_recent_mergers_and_acquisitions", False):
            if kind == "boolean" and "did" in question_text.lower():
                return {"question_text": question_text, "value": "False", "references": [{"pdf_sha1": sha1, "page_index": 0}]}
        
        # Process each page to find the answer
        best_answer = "N/A"
        best_page_idx = -1
        best_confidence = 0.0
        
        # Use metadata to prioritize certain sections of the document
        # For example, if the question is about financial performance, prioritize pages with financial statements
        priority_pages = []
        
        # Keywords that might help identify relevant sections
        financial_keywords = ["financial statements", "balance sheet", "income statement", "cash flow", "financial results"]
        leadership_keywords = ["board of directors", "executive officers", "management", "leadership"]
        risk_keywords = ["risk factors", "risks", "uncertainties"]
        
        # Identify potentially relevant pages based on keywords
        for i, page in enumerate(pages):
            page_lower = page.lower()
            
            # Check for financial information
            if any(keyword in page_lower for keyword in financial_keywords) and "financial" in question_text.lower():
                priority_pages.append(i)
            
            # Check for leadership information
            if any(keyword in page_lower for keyword in leadership_keywords) and "leadership" in question_text.lower():
                priority_pages.append(i)
            
            # Check for risk factors
            if any(keyword in page_lower for keyword in risk_keywords) and "risk" in question_text.lower():
                priority_pages.append(i)
        
        # If we found priority pages, process them first
        if priority_pages:
            # Group priority pages into batches
            batch_size = 5
            for i in range(0, len(priority_pages), batch_size):
                batch_indices = priority_pages[i:i+batch_size]
                batch_pages = [pages[idx] for idx in batch_indices]
                batch_context = "\n\n".join([f"Page {idx}: {pages[idx]}" for idx in batch_indices])
                
                answer, confidence = self.answer_question_with_llm(question_text, batch_context, kind)
                
                if confidence > best_confidence and answer != "N/A":
                    best_confidence = confidence
                    best_answer = answer
                    
                    # Find the specific page that contains the answer
                    for j, idx in enumerate(batch_indices):
                        page_answer, page_confidence = self.answer_question_with_llm(question_text, pages[idx], kind)
                        if page_answer == answer:
                            best_page_idx = idx
                            break
        
        # If we didn't find an answer in the priority pages, process all pages
        if best_answer == "N/A":
            # Process pages in batches to avoid context length issues
            batch_size = 5
            for i in range(0, len(pages), batch_size):
                # Skip batches we've already processed
                if any(i <= p < i + batch_size for p in priority_pages):
                    continue
                
                batch_pages = pages[i:i+batch_size]
                batch_context = "\n\n".join([f"Page {i+j}: {page}" for j, page in enumerate(batch_pages)])
                
                answer, confidence = self.answer_question_with_llm(question_text, batch_context, kind)
                
                if confidence > best_confidence and answer != "N/A":
                    best_confidence = confidence
                    best_answer = answer
                    
                    # Find the specific page that contains the answer
                    for j, page in enumerate(batch_pages):
                        page_answer, page_confidence = self.answer_question_with_llm(question_text, page, kind)
                        if page_answer == answer:
                            best_page_idx = i + j
                            break
        
        # Create references if we found an answer
        references = []
        if best_page_idx >= 0:
            references = [{"pdf_sha1": sha1, "page_index": best_page_idx}]
        
        return {"question_text": question_text, "value": best_answer, "references": references}
    
    def process_all_questions(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process all questions and return the answers.
        
        Returns:
            A dictionary with a list of answers
        """
        results = []
        
        for i, question_data in enumerate(self.questions):
            logger.info(f"Processing question {i+1}/{len(self.questions)}: {question_data['text'][:50]}...")
            result = self.process_question(question_data)
            results.append(result)
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)
        
        return {"answers": results}
    
    def save_results(self, results: Dict[str, List[Dict[str, Any]]], output_path: str):
        """
        Save the results to a JSON file.
        
        Args:
            results: The results to save
            output_path: The path to save the results to
        """
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Answer questions about PDF files using metadata and an LLM.')
    parser.add_argument('--pdf-dir', type=str, default=os.environ.get("PDF_DIR", os.path.expanduser("~/Downloads/pdfs")),
                        help='Directory containing PDF files (default: ~/Downloads/pdfs)')
    parser.add_argument('--pdf-meta', type=str, default="pdf-meta.json",
                        help='Path to the PDF metadata JSON file (default: pdf-meta.json)')
    parser.add_argument('--questions', type=str, default="questions.json",
                        help='Path to the questions JSON file (default: questions.json)')
    parser.add_argument('--output', type=str, default="answers.json",
                        help='Path to save the results to (default: answers.json)')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Logging level (default: INFO)')
    parser.add_argument('--single-question', type=int, default=None,
                        help='Process only a single question by index (0-based)')
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create the answerer
    answerer = PDFQuestionAnswerer(
        pdf_dir=args.pdf_dir,
        pdf_meta_path=args.pdf_meta,
        questions_path=args.questions
    )
    
    # Process questions
    if args.single_question is not None:
        # Process a single question
        if args.single_question < 0 or args.single_question >= len(answerer.questions):
            logger.error(f"Invalid question index: {args.single_question}. Must be between 0 and {len(answerer.questions)-1}.")
            return
        
        question_data = answerer.questions[args.single_question]
        logger.info(f"Processing single question: {question_data['text']}")
        result = answerer.process_question(question_data)
        results = {"answers": [result]}
    else:
        # Process all questions
        results = answerer.process_all_questions()
    
    # Save results
    answerer.save_results(results, args.output)

if __name__ == "__main__":
    main() 