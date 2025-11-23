"""
Regeneration handlers for content components
Provides callbacks that update state without UI rendering
"""
import streamlit as st
from typing import Dict, Any, Optional
from src.agent_framework import ContentAgent, MediaAgent, ChartAgent, QuizAgent, SummaryAgent, ResourceAgent
from src.state_manager import StateManager
from services.retry_service import with_retry

class RegenerationHandler:
    """Handles component regeneration without page reloads or ghost UI"""
    
    @staticmethod
    def create_content_regenerator(client, model, config, unit_index: int, unit: Dict[str, Any], metadata: Dict[str, Any]):
        """Create a callback for content regeneration"""
        def regenerate():
            try:
                # Set flag to show spinner in main flow
                StateManager.set_state(f'regenerating_content_{unit_index}', True)
                
                content_agent = ContentAgent(client, model, config)
                new_content = content_agent.generate_content(
                    unit.get('title', 'Untitled'), 
                    metadata.get('subject', 'Subject'), 
                    metadata.get('grade', 'Grade'), 
                    metadata.get('style', 'Standard'),
                    metadata.get('extra', ''),
                    metadata.get('language', 'English'),
                    metadata.get('include_keypoints', True)
                )
                
                # Update content directly in state
                StateManager.update_curriculum_unit(unit_index, "content", new_content)
                
                # Set success flag for main flow to display
                StateManager.set_state(f'content_regenerated_{unit_index}', True)
                StateManager.set_state(f'regenerating_content_{unit_index}', False)
                
            except Exception as e:
                # Set error flag for main flow to display
                StateManager.set_state(f'content_regen_error_{unit_index}', str(e))
                StateManager.set_state(f'regenerating_content_{unit_index}', False)
        
        return regenerate
    
    @staticmethod
    def create_image_regenerator(image_generator, config, unit_index: int, unit: Dict[str, Any], metadata: Dict[str, Any]):
        """Create a callback for image regeneration"""
        def regenerate():
            try:
                # Set flag to show spinner in main flow
                StateManager.set_state(f'regenerating_images_{unit_index}', True)
                
                prompt_template = config["prompts"].get("image", "")
                prompt = prompt_template.format(
                    topic=unit.get('title', 'Untitled'),
                    subject=metadata.get('subject', 'Subject'),
                    grade=metadata.get('grade', 'Grade'),
                    style=metadata.get('style', 'Standard'),
                    extra=metadata.get('extra', ''),
                    language=metadata.get('language', 'English')
                )
                
                new_images = image_generator.create_image(
                    prompt=prompt, 
                    model=metadata.get('image_model', 'gpt-imagegen-1'),
                    size=metadata.get('image_size', '1024x1024'),
                    n=3 if metadata.get('media_richness', 3) >= 5 else 1
                )
                
                # Update images and selected image in state
                StateManager.update_curriculum_unit(unit_index, "images", new_images)
                
                if new_images and new_images[0].get("b64"):
                    StateManager.update_curriculum_unit(unit_index, "selected_image_b64", new_images[0]["b64"])
                
                # Set success flag for main flow to display
                StateManager.set_state(f'images_regenerated_{unit_index}', True)
                StateManager.set_state(f'regenerating_images_{unit_index}', False)
                
            except Exception as e:
                # Set error flag for main flow to display
                StateManager.set_state(f'images_regen_error_{unit_index}', str(e))
                StateManager.set_state(f'regenerating_images_{unit_index}', False)
        
        return regenerate
    
    @staticmethod
    def create_chart_regenerator(client, model, config, unit_index: int, unit: Dict[str, Any], metadata: Dict[str, Any]):
        """Create a callback for chart regeneration"""
        def regenerate():
            try:
                # Set flag to show spinner in main flow
                StateManager.set_state(f'regenerating_chart_{unit_index}', True)
                
                chart_agent = ChartAgent(client, model, config)
                suggestion = chart_agent.suggest_chart(
                    unit.get('title', 'Untitled'),
                    metadata.get('subject', 'Subject'),
                    metadata.get('grade', 'Grade'),
                    metadata.get('style', 'Standard'),
                    metadata.get('language', 'English')
                )
                
                if suggestion:
                    StateManager.update_curriculum_unit(unit_index, "chart_suggestion", suggestion)
                    chart_result = chart_agent.create_chart(suggestion)
                    StateManager.update_curriculum_unit(unit_index, "chart", chart_result)
                    
                    # Set success flag for main flow to display
                    StateManager.set_state(f'chart_regenerated_{unit_index}', True)
                else:
                    # Set warning flag if no suitable chart
                    StateManager.set_state(f'chart_regen_warning_{unit_index}', "No suitable chart for this topic")
                
                StateManager.set_state(f'regenerating_chart_{unit_index}', False)
                
            except Exception as e:
                # Set error flag for main flow to display
                StateManager.set_state(f'chart_regen_error_{unit_index}', str(e))
                StateManager.set_state(f'regenerating_chart_{unit_index}', False)
        
        return regenerate
    
    @staticmethod
    def create_quiz_regenerator(client, model, config, unit_index: int, unit: Dict[str, Any], metadata: Dict[str, Any]):
        """Create a callback for quiz regeneration"""
        def regenerate():
            try:
                # Set flag to show spinner in main flow
                StateManager.set_state(f'regenerating_quiz_{unit_index}', True)
                
                quiz_agent = QuizAgent(client, model, config)
                
                # Clear existing quiz answers for this unit
                unit_key_base = f"unit_{unit_index}"
                current_answers = dict(st.session_state.get('quiz_answers', {}))
                current_feedback = dict(st.session_state.get('quiz_feedback', {}))
                
                keys_to_clear = [k for k in current_answers.keys() if k.startswith(unit_key_base)]
                for key in keys_to_clear:
                    current_answers.pop(key, None)
                    current_feedback.pop(key, None)
                
                # Update state atomically
                StateManager.batch_update({
                    'quiz_answers': current_answers,
                    'quiz_feedback': current_feedback
                })
                
                new_quiz = quiz_agent.generate_quiz(
                    unit.get('title', 'Untitled'),
                    metadata.get('subject', 'Subject'),
                    metadata.get('grade', 'Grade'),
                    metadata.get('style', 'Standard'),
                    metadata.get('language', 'English')
                )
                
                StateManager.update_curriculum_unit(unit_index, "quiz", new_quiz)
                
                # Set success flag for main flow to display
                StateManager.set_state(f'quiz_regenerated_{unit_index}', True)
                StateManager.set_state(f'regenerating_quiz_{unit_index}', False)
                
            except Exception as e:
                # Set error flag for main flow to display
                StateManager.set_state(f'quiz_regen_error_{unit_index}', str(e))
                StateManager.set_state(f'regenerating_quiz_{unit_index}', False)
        
        return regenerate
    
    @staticmethod
    def create_summary_regenerator(client, model, config, unit_index: int, unit: Dict[str, Any], metadata: Dict[str, Any]):
        """Create a callback for summary regeneration"""
        def regenerate():
            try:
                # Set flag to show spinner in main flow
                StateManager.set_state(f'regenerating_summary_{unit_index}', True)
                
                summary_agent = SummaryAgent(client, model, config)
                
                new_summary = summary_agent.generate_summary(
                    unit.get('title', 'Untitled'),
                    metadata.get('subject', 'Subject'),
                    metadata.get('grade', 'Grade'),
                    metadata.get('language', 'English')
                )
                
                StateManager.update_curriculum_unit(unit_index, "summary", new_summary)
                
                # Set success flag for main flow to display
                StateManager.set_state(f'summary_regenerated_{unit_index}', True)
                StateManager.set_state(f'regenerating_summary_{unit_index}', False)
                
            except Exception as e:
                # Set error flag for main flow to display
                StateManager.set_state(f'summary_regen_error_{unit_index}', str(e))
                StateManager.set_state(f'regenerating_summary_{unit_index}', False)
        
        return regenerate
