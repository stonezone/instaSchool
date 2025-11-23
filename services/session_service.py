"""
Session Management Service
Handles session state management and file operations
"""

import os
import json
import uuid
import base64
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Set


class SessionManager:
    """Manages session state and temporary files"""
    
    def __init__(self):
        """Initialize session manager"""
        self.temp_files: Set[str] = set()
        
        # Ensure required directories exist
        Path("curricula").mkdir(exist_ok=True)
        Path("exports").mkdir(exist_ok=True)
        
    def add_temp_file(self, file_path: str) -> None:
        """Add a file to the cleanup list
        
        Args:
            file_path: Path to temporary file
        """
        if file_path and os.path.exists(file_path):
            self.temp_files.add(file_path)
            
    def save_base64_to_temp_file(self, b64_data: str, suffix: str = ".png") -> Optional[str]:
        """Save base64 data to a temporary file
        
        Args:
            b64_data: Base64 encoded data
            suffix: File suffix
            
        Returns:
            Path to temporary file or None if failed
        """
        if not isinstance(b64_data, str) or not b64_data:
            return None
            
        try:
            # Ensure correct padding
            missing_padding = len(b64_data) % 4
            if missing_padding:
                b64_data += '=' * (4 - missing_padding)

            img_bytes = base64.b64decode(b64_data)
            
            # Use tempfile for secure temporary file creation
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as tf:
                tf.write(img_bytes)
                temp_path = tf.name
                
            self.add_temp_file(temp_path)
            return temp_path
            
        except (base64.binascii.Error, ValueError) as e:
            print(f"Error decoding base64 data: {e}")
            return None
            
    def cleanup_temp_files(self) -> None:
        """Clean up all temporary files"""
        for filepath in self.temp_files:
            try:
                Path(filepath).unlink(missing_ok=True)
                print(f"Deleted tmp file: {filepath}")
            except Exception as e:
                print(f"Error deleting tmp file {filepath}: {e}")
        
        self.temp_files.clear()
        
    def save_curriculum(self, curriculum: Dict[str, Any], filename: Optional[str] = None) -> tuple[bool, str]:
        """Save curriculum to JSON file
        
        Args:
            curriculum: Curriculum data
            filename: Optional filename, generates one if not provided
            
        Returns:
            Tuple of (success, message)
        """
        if not curriculum or not isinstance(curriculum, dict):
            return False, "Invalid curriculum data"
            
        try:
            # Generate filename if not provided
            if not filename:
                curr_id = curriculum.get("meta", {}).get("id", uuid.uuid4().hex)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"curriculum_{curr_id}_{timestamp}.json"
                
            save_path = Path("curricula") / Path(filename).name
            
            # Create a deep copy to avoid modifying the live data
            save_data = json.loads(json.dumps(curriculum, default=self._json_serializer))
            
            # Remove temporary file paths before saving
            for unit in save_data.get("units", []):
                if "images" in unit and isinstance(unit["images"], list):
                    for img_dict in unit["images"]:
                        if isinstance(img_dict, dict):
                            img_dict.pop("path", None)
                if "chart" in unit and isinstance(unit["chart"], dict):
                    unit["chart"].pop("path", None)
                    
            with open(save_path, "w", encoding='utf-8') as f:
                json.dump(save_data, f, indent=4)
                
            return True, f"Curriculum saved to {save_path}"
            
        except TypeError as e:
            return False, f"Data serialization error: {e}"
        except IOError as e:
            return False, f"File write error: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
            
    def load_curriculum(self, filename: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Load curriculum from JSON file
        
        Args:
            filename: Filename to load
            
        Returns:
            Tuple of (curriculum_data, error_message)
        """
        load_path = Path("curricula") / Path(filename).name
        
        if not load_path.exists():
            return None, f"File not found: {load_path}"
            
        try:
            with open(load_path, "r", encoding='utf-8') as f:
                curriculum = json.load(f)
                
            # Basic validation
            if not isinstance(curriculum, dict) or "meta" not in curriculum or "units" not in curriculum:
                return None, f"Invalid format in file {load_path}"
                
            # Recreate temporary file paths for images/charts from base64 data
            for unit in curriculum.get("units", []):
                if "images" in unit and isinstance(unit["images"], list):
                    for img_dict in unit["images"]:
                        if isinstance(img_dict, dict) and "b64" in img_dict:
                            path = self.save_base64_to_temp_file(img_dict["b64"])
                            if path:
                                img_dict["path"] = path
                                
                if "chart" in unit and isinstance(unit["chart"], dict) and "b64" in unit["chart"]:
                    chart_path = self.save_base64_to_temp_file(unit["chart"]["b64"])
                    if chart_path:
                        unit["chart"]["path"] = chart_path
                elif "chart" in unit and isinstance(unit["chart"], dict):
                    unit["chart"]["path"] = None
                    
            return curriculum, None
            
        except json.JSONDecodeError as e:
            return None, f"JSON decode error: {e}"
        except IOError as e:
            return None, f"File read error: {e}"
        except Exception as e:
            return None, f"Unexpected error: {e}"
            
    def get_saved_curricula(self) -> list[str]:
        """Get list of saved curriculum files
        
        Returns:
            List of filenames sorted by modification time (newest first)
        """
        try:
            saved_files = sorted(
                Path("curricula").glob("curriculum_*.json"), 
                key=os.path.getmtime, 
                reverse=True
            )
            return [f.name for f in saved_files]
        except Exception as e:
            print(f"Error listing saved curricula: {e}")
            return []
            
    def _json_serializer(self, obj) -> str:
        """JSON serializer for non-standard types
        
        Args:
            obj: Object to serialize
            
        Returns:
            Serialized string representation
        """
        if isinstance(obj, (datetime, Path)):
            return str(obj)
        if hasattr(obj, 'to_json'):
            return obj.to_json()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)


class QuizManager:
    """Manages quiz state and interactions"""
    
    @staticmethod
    def update_quiz_answer(quiz_answers: Dict[str, str], quiz_feedback: Dict[str, bool], 
                          q_key: str, user_answer: str, correct_answer: str, 
                          case_sensitive: bool = True) -> tuple[Dict[str, str], Dict[str, bool], bool]:
        """Safely update quiz answer
        
        Args:
            quiz_answers: Current quiz answers dict
            quiz_feedback: Current quiz feedback dict
            q_key: Question key
            user_answer: User's answer
            correct_answer: Correct answer
            case_sensitive: Whether comparison should be case sensitive
            
        Returns:
            Tuple of (updated_answers, updated_feedback, success)
        """
        try:
            # Create copies to avoid modifying original dicts
            new_answers = dict(quiz_answers)
            new_feedback = dict(quiz_feedback)
            
            # Compare answers
            if case_sensitive:
                is_correct = (user_answer == correct_answer)
            else:
                is_correct = (user_answer.strip().lower() == correct_answer.strip().lower())
                
            new_answers[q_key] = user_answer
            new_feedback[q_key] = is_correct
            
            return new_answers, new_feedback, True
            
        except Exception as e:
            print(f"Quiz update error: {e}")
            return quiz_answers, quiz_feedback, False
            
    @staticmethod
    def clear_unit_quiz_data(quiz_answers: Dict[str, str], quiz_feedback: Dict[str, bool], 
                           unit_key_base: str) -> tuple[Dict[str, str], Dict[str, bool]]:
        """Clear quiz data for a specific unit
        
        Args:
            quiz_answers: Current quiz answers
            quiz_feedback: Current quiz feedback
            unit_key_base: Base key for the unit (e.g., "unit_0")
            
        Returns:
            Tuple of (cleaned_answers, cleaned_feedback)
        """
        new_answers = {k: v for k, v in quiz_answers.items() if not k.startswith(f"{unit_key_base}_q_")}
        new_feedback = {k: v for k, v in quiz_feedback.items() if not k.startswith(f"{unit_key_base}_q_")}
        
        return new_answers, new_feedback


class InputValidator:
    """Validates and sanitizes user inputs"""
    
    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """Sanitize user prompts for API safety
        
        Args:
            prompt: User input prompt
            
        Returns:
            Sanitized prompt
        """
        if not prompt or not isinstance(prompt, str):
            return ""
            
        # Remove potentially problematic content
        sanitized = prompt.strip()
        
        # Limit length
        if len(sanitized) > 2000:
            sanitized = sanitized[:2000] + "..."
            
        # Remove script tags and other HTML
        import re
        sanitized = re.sub(r'<script.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'<.*?>', '', sanitized)
        
        return sanitized
        
    @staticmethod
    def validate_subject(subject: str) -> bool:
        """Validate subject input
        
        Args:
            subject: Subject string
            
        Returns:
            True if valid
        """
        if not subject or not isinstance(subject, str):
            return False
            
        # Basic length and content validation
        return len(subject.strip()) > 0 and len(subject) < 500
        
    @staticmethod
    def validate_grade(grade: str) -> bool:
        """Validate grade input
        
        Args:
            grade: Grade string
            
        Returns:
            True if valid
        """
        if not grade or not isinstance(grade, str):
            return False
            
        valid_grades = ["Preschool", "Kindergarten"] + [str(i) for i in range(1, 13)] + ["University"]
        return grade in valid_grades