from pdf2image import convert_from_path
from PIL import Image
from pathlib import Path
import os

def merge_pdf_to_image(pdf_path: str, dpi: int = 200) -> Image.Image:
    pages = convert_from_path(pdf_path, dpi=dpi)

    if not pages:
        raise ValueError(f"No pages found in PDF: {pdf_path}")

    widths, heights = zip(*(page.size for page in pages))
    max_width = max(widths)
    total_height = sum(heights)

    merged_image = Image.new("RGB", (max_width, total_height), "white")

    y_offset = 0
    for page in pages:
        merged_image.paste(page, (0, y_offset))
        y_offset += page.height

    return merged_image

def process_pdf_folder(input_folder: str, output_folder: str, dpi: int = 200):
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_path.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found.")
        return

    for pdf_file in pdf_files:
        try:
            print(f"Processing: {pdf_file.name}")
            merged_image = merge_pdf_to_image(str(pdf_file), dpi=dpi)

            output_file = output_path / (pdf_file.stem + ".jpg")
            merged_image.save(output_file, "JPEG")
            print(f"Saved: {output_file}")

        except Exception as e:
            print(f"Failed to process {pdf_file.name}: {e}")

if __name__ == "__main__":
    input_pdf_folder = r"C:\Users\Disha\Downloads\gemini_resume_parse\project\merge_image"
    output_image_folder = r"C:\Users\Disha\Downloads\gemini_resume_parse\project\resumes"

    process_pdf_folder(input_pdf_folder, output_image_folder)
