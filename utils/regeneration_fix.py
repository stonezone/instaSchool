"""
Regeneration handlers for content components
Provides callbacks that update state without st.rerun()
"""
import streamlit as st
from typing import Dict, Any, Optional
from src.agent_framework import ContentAgent, MediaAgent, ChartAgent, QuizAgent, SummaryAgent, ResourceAgent
from services.retry_service import with_retry
import time

class RegenerationHandler:
    """Handles component regeneration without page reloads"""
    
    @staticmethod
    def create_content_regenerator(client, model, config, unit_index: int, unit: Dict[str, Any], metadata: Dict[str, Any]):
        """Create a callback for content regeneration"""
        def regenerate():
            container = st.empty()
            with container.container():
                with st.spinner(f"Regenerating content for Unit {unit_index+1}: {unit.get('title', 'Untitled')}..."):
                    try:
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
                        # Update content directly
                        st.session_state.curriculum["units"][unit_index]["content"] = new_content
                        container.success("✅ Content regenerated successfully!")
                        time.sleep(1)
                        container.empty()
                    except Exception as e:
                        container.error(f"Failed to regenerate content: {str(e)}")
                        time.sleep(3)
                        container.empty()
        return regenerate
    
    @staticmethod
    def create_image_regenerator(image_generator, config, unit_index: int, unit: Dict[str, Any], metadata: Dict[str, Any]):
        """Create a callback for image regeneration"""
        def regenerate():
            container = st.empty()
            with container.container():
                with st.spinner(f"Regenerating images for Unit {unit_index+1}: {unit.get('title', 'Untitled')}..."):
                    try:
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
                        
                        # Update images and selected image
                        st.session_state.curriculum["units"][unit_index]["images"] = new_images
                        if new_images and new_images[0].get("b64"):
                            st.session_state.curriculum["units"][unit_index]["selected_image_b64"] = new_images[0]["b64"]
                        
                        container.success("✅ Images regenerated successfully!")
                        time.sleep(1)
                        container.empty()
                    except Exception as e:
                        container.error(f"Failed to regenerate images: {str(e)}")
                        time.sleep(3)
                        container.empty()
        return regenerate
    
    @staticmethod
    def create_chart_regenerator(client, model, config, unit_index: int, unit: Dict[str, Any], metadata: Dict[str, Any]):
        """Create a callback for chart regeneration"""
        def regenerate():
            container = st.empty()
            with container.container():
                with st.spinner(f"Regenerating chart for Unit {unit_index+1}: {unit.get('title', 'Untitled')}..."):
                    try:
                        chart_agent = ChartAgent(client, model, config)
                        suggestion = chart_agent.suggest_chart(
                            unit.get('title', 'Untitled'),
                            metadata.get('subject', 'Subject'),
                            metadata.get('grade', 'Grade'),
                            metadata.get('style', 'Standard'),
                            metadata.get('language', 'English')
                        )
                        
                        if suggestion:
                            st.session_state.curriculum["units"][unit_index]["chart_suggestion"] = suggestion
                            st.session_state.curriculum["units"][unit_index]["chart"] = chart_agent.create_chart(suggestion)
                            container.success("✅ Chart regenerated successfully!")
                        else:
                            container.warning("No suitable chart for this topic")
                        
                        time.sleep(1)
                        container.empty()
                    except Exception as e:
                        container.error(f"Failed to regenerate chart: {str(e)}")
                        time.sleep(3)
                        container.empty()
        return regenerate
    
    @staticmethod
    def create_quiz_regenerator(client, model, config, unit_index: int, unit: Dict[str, Any], metadata: Dict[str, Any]):
        """Create a callback for quiz regeneration"""
        def regenerate():
            container = st.empty()
            with container.container():
                with st.spinner(f"Regenerating quiz for Unit {unit_index+1}: {unit.get('title', 'Untitled')}..."):
                    try:
                        quiz_agent = QuizAgent(client, model, config)
                        
                        # Clear existing quiz answers for this unit
                        unit_key_base = f"unit_{unit_index}"
                        keys_to_clear = [k for k in st.session_state.quiz_answers.keys() if k.startswith(unit_key_base)]
                        for key in keys_to_clear:
                            st.session_state.quiz_answers.pop(key, None)
                            st.session_state.quiz_feedback.pop(key, None)
                        
                        new_quiz = quiz_agent.generate_quiz(
                            unit.get('title', 'Untitled'),
                            metadata.get('subject', 'Subject'),
                            metadata.get('grade', 'Grade'),
                            metadata.get('style', 'Standard'),
                            metadata.get('language', 'English')
                        )
                        
                        st.session_state.curriculum["units"][unit_index]["quiz"] = new_quiz
                        container.success("✅ Quiz regenerated successfully!")
                        time.sleep(1)
                        container.empty()
                    except Exception as e:
                        container.error(f"Failed to regenerate quiz: {str(e)}")
                        time.sleep(3)
                        container.empty()
        return regenerate
    
    @staticmethod
    def create_summary_regenerator(client, model, config, unit_index: int, unit: Dict[str, Any], metadata: Dict[str, Any]):
        """Create a callback for summary regeneration"""
        def regenerate():
            container = st.empty()
            with container.container():
                with st.spinner(f"Regenerating summary for Unit {unit_index+1}: {unit.get('title', 'Untitled')}..."):
                    try:
                        summary_agent = SummaryAgent(client, model, config)
                        
                        new_summary = summary_agent.generate_summary(
                            unit.get('title', 'Untitled'),
                            metadata.get('subject', 'Subject'),
                            metadata.get('grade', 'Grade'),
                            metadata.get('language', 'English')
                        )
                        
                        st.session_state.curriculum["units"][unit_index]["summary"] = new_summary
                        container.success("✅ Summary regenerated successfully!")
                        time.sleep(1)
                        container.empty()
                    except Exception as e:
                        container.error(f"Failed to regenerate summary: {str(e)}")
                        time.sleep(3)
                        container.empty()
        return regenerate