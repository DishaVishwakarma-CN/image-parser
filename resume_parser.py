import google.generativeai as genai
import json
from PIL import Image
import io
from typing import Dict, Any, Optional, List
import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import re

class ResumeParser:
    def __init__(self, csv_path: str | Path = "output/resumes.csv"):
        load_dotenv()
        
        api_key = os.getenv('GOOGLE_API_KEY')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # pandas-CSV setup
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

        # stable column order
        self.csv_fields = [
            "filename",
            "name",
            "email",
            "number",
            "education",
            "work_experience",
            "projects",
            "certifications",
            "skills",
        ]

        # make sure an empty CSV with header exists (only first run)
        if not self.csv_path.exists():
            pd.DataFrame(columns=self.csv_fields).to_csv(
                self.csv_path, index=False, encoding="utf-8"
            )
    
    def format_number(self,raw_number: str) -> str:
        if not raw_number:
            return ""
        cleaned = re.sub(r'\+91-?|\D', '', raw_number)
        numbers = re.findall(r'\d{10}', cleaned)
        return ', '.join(numbers)
    
    def parse_resume_from_image(self, image_path: str) -> Dict[str, Any]:
        try:
            image = Image.open(image_path)
            prompt = """
            Analyze this resume image and extract all information in the following JSON structure:
            
            {
                "name": "",
                "email": "",
                "number": ""(it should contain particular format like +91-XXXXXXXXXX),
                "education": "",
                "work_experience":"",
                "projects":"",
                "certifications": "",
                "skills":""
            }
            
            Please extract ALL information visible in the resume and return ONLY the JSON object with no additional text.
            If a field is not present in the resume, leave it empty or as an empty array.
            For 'number', extract the phone number.
            For 'work_experience', include internships and job experiences.
            """
            response = self.model.generate_content([prompt, image])
            
            json_text = response.text.strip()
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()
            parsed_data = json.loads(json_text)
            # Format the phone number
            parsed_data["number"] = self.format_number(parsed_data.get("number", ""))

            
            return {
                "success": True,
                "data": parsed_data,
                "error": None,
                "filename": os.path.basename(image_path)
            }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "data": None,
                "error": f"Failed to parse JSON response: {str(e)}",
                "filename": os.path.basename(image_path)
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Error processing resume: {str(e)}",
                "filename": os.path.basename(image_path)
            }
    def append_parsed_resume(self, parsed_result: dict) -> None:
        """Append one résumé as a row to the master CSV using pandas."""
        row = {"filename": parsed_result["filename"], **parsed_result["data"]}
        # guarantee all expected columns (missing -> "")
        row = {k: row.get(k, "") for k in self.csv_fields}

        df = pd.DataFrame([row])
        # header=True only if file was just created
        header_needed = self.csv_path.stat().st_size == 0
        df.to_csv(
            self.csv_path,
            mode="a",
            header=header_needed,
            index=False,
            encoding="utf-8",
        )
    
    def process_resume_folder(self, folder_path: str, extensions: List[str] = None) -> Dict[str, Any]:
        if extensions is None:
            extensions = ['.jpg', '.jpeg', '.png']
        
        folder = Path(folder_path)        
        results = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "processed_files": [],
            "failed_files": []
        }
        image_files = []
        for ext in extensions:
            image_files.extend(folder.glob(f"*{ext}"))
        
        results["total"] = len(image_files)
        
        print(f"Found {results['total']} resume images to process...")
        
        for idx, image_path in enumerate(image_files, 1):
            print(f"\nProcessing {idx}/{results['total']}: {image_path.name}")
            parsed_result = self.parse_resume_from_image(str(image_path))

            if parsed_result["success"]:
                self.append_parsed_resume(parsed_result)
                results["successful"] += 1
                results["processed_files"].append({
                    "source": str(image_path),
                    "output": str(self.csv_path),
                    "name": parsed_result["data"].get("name", "Unknown")
                })
                print(f"✓ Added to CSV → {self.csv_path}")
            else:
                results["failed"] += 1
                results["failed_files"].append({
                    "source": str(image_path),
                    "error": parsed_result["error"]
                })
                print(f"✗ Failed: {parsed_result['error']}")
        return results

if __name__ == "__main__":
    parser = ResumeParser("csv_file.csv")
    parser.process_resume_folder("resumes")