import json
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description='Find metadata for a specific company.')
    parser.add_argument('company_name', type=str, help='Name of the company to search for')
    parser.add_argument('--pdf-meta', type=str, default="pdf-meta.json",
                        help='Path to the PDF metadata JSON file (default: pdf-meta.json)')
    parser.add_argument('--fuzzy', action='store_true',
                        help='Enable fuzzy matching for company names')
    
    args = parser.parse_args()
    
    # Load metadata
    try:
        with open(args.pdf_meta, 'r') as f:
            pdf_meta = json.load(f)
    except Exception as e:
        print(f"Error loading metadata file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Create a mapping from company name to metadata
    company_to_meta = {
        meta["company_name"].lower(): meta 
        for meta in pdf_meta
    }
    
    # Try exact match first
    company_lower = args.company_name.lower()
    if company_lower in company_to_meta:
        meta = company_to_meta[company_lower]
        print(f"Found exact match for '{args.company_name}':")
        print(json.dumps(meta, indent=2))
        sys.exit(0)
    
    # If no exact match and fuzzy matching is enabled, try fuzzy matching
    if args.fuzzy:
        print(f"No exact match found for '{args.company_name}'. Trying fuzzy matching...")
        
        # Simple word overlap score
        best_matches = []
        for comp_name, meta in company_to_meta.items():
            words1 = set(company_lower.split())
            words2 = set(comp_name.split())
            overlap = len(words1.intersection(words2))
            
            if overlap > 0:
                best_matches.append((overlap, comp_name, meta))
        
        # Sort by overlap score (descending)
        best_matches.sort(reverse=True)
        
        if best_matches:
            print(f"Found {len(best_matches)} potential matches:")
            for i, (score, comp_name, meta) in enumerate(best_matches[:5]):
                print(f"\n{i+1}. '{meta['company_name']}' (score: {score}):")
                print(f"   SHA1: {meta['sha1']}")
                print(f"   Industry: {meta['major_industry']}")
            
            # Ask user to select a match
            while True:
                try:
                    choice = input("\nEnter the number of the match to show full details (or 'q' to quit): ")
                    if choice.lower() == 'q':
                        break
                    
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(best_matches[:5]):
                        _, _, meta = best_matches[choice_idx]
                        print("\nFull metadata:")
                        print(json.dumps(meta, indent=2))
                        break
                    else:
                        print("Invalid choice. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'q'.")
        else:
            print(f"No matches found for '{args.company_name}'.")
    else:
        print(f"No exact match found for '{args.company_name}'. Use --fuzzy to enable fuzzy matching.")

if __name__ == "__main__":
    main() 