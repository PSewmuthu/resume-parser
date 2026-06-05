import os
import json
from tqdm import tqdm
from src.text_extractor import TextExtractor
from src.entity_extractor import EntityExtractor


def main():
    # Create processed cv json files for each cv in the raw_resumes directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    raw_resumes_dir = os.path.join(current_dir, 'data', 'raw_resumes')
    processed_dir = os.path.join(current_dir, 'data', 'processed')

    os.makedirs(processed_dir, exist_ok=True)

    for filename in tqdm(os.listdir(raw_resumes_dir), desc="Processing resumes"):
        extension = os.path.splitext(filename)[1].lower()

        if extension in ['.pdf', '.docx', '.txt']:
            file_path = os.path.join(raw_resumes_dir, filename)

            # Extract text from the file
            text_extractor = TextExtractor(file_path)
            text = text_extractor.extract()

            # Extract entities from the extracted text
            entity_extractor = EntityExtractor(text)
            entities = entity_extractor.extract_entities()

            # Save the processed data as JSON
            output_path = os.path.join(
                processed_dir, f"{os.path.splitext(filename)[0]}.json")
            with open(output_path, 'w') as f:
                json.dump(entities, f, indent=4)

    print("Processing complete.")


if __name__ == "__main__":
    main()
