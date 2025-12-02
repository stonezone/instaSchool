"""
Agent Framework for Curriculum Generation
Implements an orchestrator-worker pattern where a coordinator agent delegates tasks to specialized agents
"""

import os
import json
import time
import base64
import httpx
import concurrent.futures
import threading
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

# Import BaseAgent from core.types to prevent circular dependencies
from src.core.types import BaseAgent
from src.audio_agent import AudioAgent
from src.constants import LLM_TEMPERATURE_DEFAULT

# Try to import matplotlib, but provide a fallback for testing
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    print("Warning: matplotlib not installed, chart generation will not work.")
    MATPLOTLIB_AVAILABLE = False


class OrchestratorAgent(BaseAgent):
    """Main agent that coordinates the curriculum generation process"""

    # Persona mapping for subject-based tutor personalities
    PERSONA_MAP = {
        "physics": {
            "name": "Albert Einstein",
            "style": "a curious, wonder-filled style that explores the mysteries of the universe"
        },
        "history": {
            "name": "George Washington",
            "style": "a storytelling style that brings historical events to life"
        },
        "math": {
            "name": "Ada Lovelace",
            "style": "a logical, step-by-step style that celebrates mathematical elegance"
        },
        "science": {
            "name": "Marie Curie",
            "style": "an inquisitive, experimental style that encourages discovery"
        },
        "literature": {
            "name": "William Shakespeare",
            "style": "a dramatic, expressive style that brings stories and words to life"
        },
        "default": {
            "name": "a friendly tutor",
            "style": "an encouraging, supportive style"
        }
    }

    def __init__(self, client, model="gpt-5-nano", worker_model="gpt-5-nano"):
        super().__init__(client, model)
        self.worker_model = worker_model

    def get_persona_for_subject(self, subject: str) -> Dict[str, str]:
        """
        Get the appropriate persona based on the subject.

        Args:
            subject: The curriculum subject

        Returns:
            Dict with 'name' and 'style' keys for the persona
        """
        # Normalize subject to lowercase for matching
        subject_lower = subject.lower() if subject else ""

        # Check for keyword matches in subject
        for key, persona in self.PERSONA_MAP.items():
            if key != "default" and key in subject_lower:
                return persona

        return self.PERSONA_MAP["default"]

    def create_curriculum(
        self,
        subject,
        grade,
        style,
        language,
        extra,
        config,
        cancellation_event: Optional[threading.Event] = None,
    ):
        """Main entry point for curriculum generation.

        The optional ``cancellation_event`` allows cooperative cancellation from
        the caller or UI layer without touching Streamlit session state from
        background threads.
        """

        def is_cancelled() -> bool:
            """Check whether generation has been cancelled.

            Priority: explicit cancellation_event → StateManager.generating flag.
            """
            # Explicit cancellation token from caller takes precedence
            if cancellation_event is not None and cancellation_event.is_set():
                return True

            # Fallback to StateManager flag (main thread only)
            try:
                from src.state_manager import StateManager  # Local import to avoid cycles

                generating = StateManager.get_state("generating", True)
            except Exception:
                generating = True

            if not generating and cancellation_event is not None:
                # Propagate cancellation to worker tasks
                cancellation_event.set()
            return not generating

        # Create a plan for curriculum generation
        plan = self._create_generation_plan(subject, grade, style, language, extra)

        # Check for cancellation
        if is_cancelled():
            print("Generation cancelled during planning phase")
            return {"meta": {"cancelled": True}, "units": []}

        # Initialize worker agents with appropriate models
        outline_agent = OutlineAgent(self.client, self.worker_model, config)
        content_agent = ContentAgent(self.client, self.worker_model, config)
        media_agent = MediaAgent(self.client, config)  # Note: MediaAgent uses image models, not text models
        chart_agent = ChartAgent(self.client, self.worker_model, config)
        quiz_agent = QuizAgent(self.client, self.worker_model, config)
        summary_agent = SummaryAgent(self.client, self.worker_model, config)
        resource_agent = ResourceAgent(self.client, self.worker_model, config)
        
        # Step 1: Generate outline
        topics = outline_agent.generate_outline(
            subject,
            grade,
            style,
            extra,
            config["defaults"]["min_topics"],
            config["defaults"]["max_topics"],
            language,
        )

        # Check for cancellation
        if is_cancelled():
            print("Generation cancelled after outline phase")
            return {"meta": {"cancelled": True}, "units": []}
        
        # Get persona based on subject
        persona = self.get_persona_for_subject(subject)

        # Initialize curriculum structure
        curriculum = {
            "meta": {
                "subject": subject,
                "grade": grade,
                "style": style,
                "language": language,
                "extra": extra,
                "plan": plan,
                "include_quizzes": config["defaults"]["include_quizzes"],
                "include_summary": config["defaults"]["include_summary"],
                "include_resources": config["defaults"]["include_resources"],
                "include_keypoints": config["defaults"]["include_keypoints"],
                "media_richness": config["defaults"]["media_richness"],
                "persona": persona,
            },
            "units": []
        }
        
        # Process each topic concurrently or sequentially as needed
        for i, topic in enumerate(topics):
            # Check for cancellation
            if is_cancelled():
                print(f"Generation cancelled after processing {i} of {len(topics)} topics")
                return curriculum  # Return what we have so far

            # Provide detailed instructions to content agent based on plan
            unit = self._process_topic(
                topic,
                subject,
                grade,
                style,
                language,
                extra,
                content_agent,
                media_agent,
                chart_agent,
                quiz_agent,
                summary_agent,
                resource_agent,
                config,
                cancellation_event=cancellation_event,
            )
            curriculum["units"].append(unit)

            # Update progress in session state after each unit (best-effort)
            try:
                from src.state_manager import StateManager  # Local import

                topic_progress = 0.6 / max(len(topics), 1)
                StateManager.update_state(
                    "progress", 0.3 + (i + 1) * topic_progress
                )
            except Exception:
                # If StateManager or Streamlit are unavailable, skip UI progress updates
                pass

        # Check for cancellation before refinement
        if is_cancelled():
            print("Generation cancelled before refinement")
            return curriculum
            
        # Final review and refinement
        curriculum = self._refine_curriculum(curriculum)
        return curriculum
    
    def _create_generation_plan(self, subject, grade, style, language, extra):
        """Create a detailed plan for generating the curriculum"""
        messages = [
            {"role": "system", "content": 
                "You are a curriculum planning specialist. Create a detailed plan for generating an educational curriculum."},
            {"role": "user", "content": 
                f"Create a detailed plan for generating a {style} curriculum for {subject} at grade {grade} in {language}. "
                f"Additional guidelines: {extra}\n\n"
                f"The plan should include: 1) How topics should be structured, 2) What teaching approaches to use, "
                f"3) What visual aids would be most effective, 4) How to assess understanding, and 5) How topics should build on each other."
            }
        ]
        
        response = self._call_model(messages)
        if response and response.choices:
            return response.choices[0].message.content
        return "Standard curriculum generation plan"
    
    def _process_topic(
        self,
        topic,
        subject,
        grade,
        style,
        language,
        extra,
        content_agent,
        media_agent,
        chart_agent,
        quiz_agent,
        summary_agent,
        resource_agent,
        config,
        cancellation_event: Optional[threading.Event] = None,
    ):
        """Process a single topic with parallel execution of auxiliary agents.

        Performance optimization: After generating core content (blocking),
        auxiliary agents (media, chart, quiz, summary, resources) run in parallel
        since they depend on content but not on each other.

        Expected speedup: 40-60% reduction in per-topic processing time.
        """
        topic_title = topic.get("title", "Untitled Topic")

        # Initialize unit structure
        unit = {
            "title": topic_title,
            "content": "",
            "images": [],
            "selected_image_b64": None,
            "chart": None,
            "chart_suggestion": None,
            "quiz": None,
            "summary": "",
            "resources": ""
        }

        # 1. Generate CORE content first (Blocking) - other agents need this
        unit["content"] = content_agent.generate_content(
            topic_title, subject, grade, style, extra, language,
            config["defaults"]["include_keypoints"]
        )

        # Store references for closures
        content = unit["content"]
        media_richness = config["defaults"]["media_richness"]

        # 2. Define parallel tasks as closures
        def run_media():
            """Generate images with content-aware prompts (slowest operation)."""
            if cancellation_event is not None and cancellation_event.is_set():
                return []
            if media_richness >= 2 and content:
                num_images = 3 if media_richness >= 5 else 1
                try:
                    # Create an image prompt agent with the same model as the worker
                    image_prompt_agent = ImagePromptAgent(self.client, self.worker_model, config)

                    # Generate a custom prompt based on the actual content
                    custom_prompt = image_prompt_agent.create_image_prompt(
                        content, topic_title, subject, grade, style, language
                    )

                    if not custom_prompt:
                        print("Warning: Could not generate custom image prompt, using default template")

                    return media_agent.create_images(
                        topic_title, subject, grade, style, language,
                        n=num_images, custom_prompt=custom_prompt
                    )
                except Exception as e:
                    print(f"Error in media generation: {e}")
                    return []
            return []

        def run_chart():
            """Generate chart suggestion and visualization."""
            if cancellation_event is not None and cancellation_event.is_set():
                return None
            if media_richness >= 3:
                try:
                    suggestion = chart_agent.suggest_chart(
                        topic_title, subject, grade, style, language
                    )
                    if suggestion:
                        return {"suggestion": suggestion, "chart": chart_agent.create_chart(suggestion)}
                except Exception as e:
                    print(f"Error in chart generation: {e}")
            return None

        def run_quiz():
            """Generate quiz questions."""
            if cancellation_event is not None and cancellation_event.is_set():
                return None
            if config["defaults"]["include_quizzes"]:
                try:
                    return quiz_agent.generate_quiz(
                        topic_title, subject, grade, style, language
                    )
                except Exception as e:
                    print(f"Error in quiz generation: {e}")
            return None

        def run_summary():
            """Generate lesson summary."""
            if cancellation_event is not None and cancellation_event.is_set():
                return ""
            if config["defaults"]["include_summary"]:
                try:
                    return summary_agent.generate_summary(
                        topic_title, subject, grade, language
                    )
                except Exception as e:
                    print(f"Error in summary generation: {e}")
            return ""

        def run_resources():
            """Generate learning resources."""
            if cancellation_event is not None and cancellation_event.is_set():
                return ""
            if config["defaults"]["include_resources"]:
                try:
                    return resource_agent.generate_resources(
                        topic_title, subject, grade, language
                    )
                except Exception as e:
                    print(f"Error in resources generation: {e}")
            return ""

        # 3. Execute parallel tasks using ThreadPoolExecutor
        # Using 5 workers for 5 independent tasks (media, chart, quiz, summary, resources)
        if cancellation_event is not None and cancellation_event.is_set():
            return unit

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_media = executor.submit(run_media)
            future_chart = executor.submit(run_chart)
            future_quiz = executor.submit(run_quiz)
            future_summary = executor.submit(run_summary)
            future_resources = executor.submit(run_resources)

            # Collect results (will block until each completes)
            # Using result() with no timeout - let individual tasks handle their own timeouts
            images = future_media.result()
            chart_res = future_chart.result()
            unit["quiz"] = future_quiz.result()
            unit["summary"] = future_summary.result()
            unit["resources"] = future_resources.result()

        # 4. Process results
        unit["images"] = images
        if unit["images"]:
            # Find the first valid image with b64 data
            for img in unit["images"]:
                if img.get("b64"):
                    unit["selected_image_b64"] = img["b64"]
                    break

        if chart_res:
            unit["chart_suggestion"] = chart_res["suggestion"]
            unit["chart"] = chart_res["chart"]

        return unit
    
    def _refine_curriculum(self, curriculum):
        """Perform final refinements on the entire curriculum"""
        messages = [
            {"role": "system", "content": 
                "You are a curriculum review specialist. Review this curriculum for coherence and consistency."},
            {"role": "user", "content": 
                f"Review this curriculum for {curriculum['meta']['subject']} at grade {curriculum['meta']['grade']}. "
                f"Check that topics build on each other logically, content is appropriate for the grade level, "
                f"and all components follow a consistent style and approach.\n\n"
                f"Curriculum topics: {[unit['title'] for unit in curriculum['units']]}"
            }
        ]
        
        response = self._call_model(messages)
        if response and response.choices:
            curriculum["meta"]["review_notes"] = response.choices[0].message.content
        
        return curriculum


class OutlineAgent(BaseAgent):
    """Agent responsible for generating the curriculum outline and topics"""
    
    def __init__(self, client, model, config):
        super().__init__(client, model)
        self.prompt_template = config["prompts"].get("outline", "")
    
    def generate_outline(self, subject, grade, style, extra, min_topics, max_topics, language) -> List[Dict[str, Any]]:
        # Create cache parameters
        cache_params = {
            'subject': subject,
            'grade': grade,
            'style': style,
            'extra': extra,
            'min_topics': min_topics,
            'max_topics': max_topics,
            'language': language
        }
        
        sys_prompt = self.prompt_template.format(
            subject=subject, grade=grade, style=style, extra=extra,
            min_topics=min_topics, max_topics=max_topics, language=language)
        
        try:
            response = self._call_model_cached(
                "outlines",
                cache_params,
                [{"role": "system", "content": sys_prompt}],
                response_format={"type": "json_object"},
                temperature=LLM_TEMPERATURE_DEFAULT
            )
            
            if response and response.choices:
                content = response.choices[0].message.content
                try:
                    data = json.loads(content)
                    topics_list = data.get("topics", [])
                    return [{"title": topic} for topic in topics_list]
                except json.JSONDecodeError:
                    print(f"JSON decode error: {content}")
            return []
        except Exception as e:
            print(f"Outline generation error: {e}")
            return []


class ContentAgent(BaseAgent):
    """Agent responsible for generating the main lesson content"""

    def __init__(self, client, model, config):
        super().__init__(client, model)
        self.prompt_template = config["prompts"].get("content", "")

    def generate_content(self, topic, subject, grade, style, extra, language, include_keypoints, stream: bool = False):
        """Generate lesson content with optional streaming support.

        Args:
            topic: The topic to generate content for
            subject: The subject area
            grade: The grade level
            style: The teaching style
            extra: Additional requirements/guidelines
            language: The language for content
            include_keypoints: Whether to include key takeaways
            stream: If True, yields content chunks as they arrive (generator mode)
                   If False, returns complete content (default behavior)

        Returns:
            str: Complete content (when stream=False)
            Generator[str, None, str]: Content chunks generator (when stream=True)
        """
        # Create cache parameters
        cache_params = {
            'topic': topic,
            'subject': subject,
            'grade': grade,
            'style': style,
            'extra': extra,
            'language': language,
            'include_keypoints': include_keypoints
        }

        keypoints_instruction = "Include a concise list of key takeaways or learning points at the end, formatted with Markdown bullet points." if include_keypoints else ""

        sys_prompt = self.prompt_template.format(
            topic=topic or "[Topic Missing]",
            subject=subject or "[Subject Missing]",
            grade=grade or "[Grade Missing]",
            style=style or "[Style Missing]",
            extra=extra or "[No Extra Guidelines]",
            language=language or "English",
            include_keypoints_instruction=keypoints_instruction
        )

        messages = [{"role": "system", "content": sys_prompt}]

        # If streaming is requested, use the streaming method
        if stream:
            return self._generate_content_streaming(messages, cache_params)

        # Otherwise, use standard cached generation (backward compatible)
        try:
            response = self._call_model_cached(
                "content",
                cache_params,
                messages,
                temperature=0.7
            )

            if response and response.choices:
                return response.choices[0].message.content
            return ""
        except Exception as e:
            print(f"Content generation error: {e}")
            return f"[Error: Content generation failed - {str(e)}]"

    def _generate_content_streaming(self, messages, cache_params):
        """Internal method for streaming content generation.

        Args:
            messages: Messages for the API call
            cache_params: Parameters for cache lookup

        Yields:
            str: Content chunks as they arrive

        Returns:
            str: Complete content after streaming
        """
        # Check cache first
        if self.cache:
            cached_content = self.cache.get_similar_content("content", cache_params)
            if cached_content:
                # Yield cached content in simulated chunks for consistent behavior
                chunk_size = 50  # Characters per chunk
                for i in range(0, len(cached_content), chunk_size):
                    yield cached_content[i:i + chunk_size]
                return cached_content

        # If no cache hit, stream from API
        try:
            full_response = ""
            for chunk in self._call_model_streaming(messages, temperature=0.7):
                full_response += chunk
                yield chunk

            # Cache the complete response
            if full_response and self.cache:
                self.cache.content_cache.cache_content("content", cache_params, full_response)

            return full_response

        except Exception as e:
            error_msg = f"[Error: Streaming content generation failed - {str(e)}]"
            print(f"Streaming content generation error: {e}")
            yield error_msg
            return error_msg


class MediaAgent:
    """Agent responsible for generating images using ImageGenerator"""

    def __init__(self, client, config):
        self.config = config  # Store full config to access defaults
        self.prompt_template = config["prompts"].get("image", "")
        self.client = client
        self.images_enabled = True

        # Try to import the logger early
        try:
            from src.verbose_logger import get_logger
            self.logger = get_logger()
        except ImportError:
            self.logger = None

        # Initialize ImageGenerator with proper model
        # IMPORTANT: Images require OpenAI - use dedicated client if main client is different provider
        from src.image_generator import ImageGenerator
        import os

        default_model = config["defaults"].get("image_model", "gpt-image-1")
        image_client = client  # Default to main client

        # Check if main client is NOT OpenAI (e.g., Kimi) - need separate OpenAI client for images
        openai_api_key = os.getenv("OPENAI_API_KEY")
        client_base_url = getattr(client, '_base_url', None) or getattr(client, 'base_url', None)
        is_openai_client = client_base_url is None or 'api.openai.com' in str(client_base_url)

        # If we're not using an OpenAI client and no OpenAI API key is configured,
        # disable image generation gracefully (text-only curricula still work).
        if not is_openai_client and not openai_api_key:
            self.images_enabled = False
            if self.logger:
                self.logger.log_info(
                    "MediaAgent: OPENAI_API_KEY not set and provider is not OpenAI; "
                    "disabling image generation (text-only output)."
                )
            self.image_generator = ImageGenerator(image_client, default_model)
            return

        if not is_openai_client and openai_api_key:
            try:
                from openai import OpenAI
                image_client = OpenAI(api_key=openai_api_key)
                if self.logger:
                    self.logger.log_event("INFO", "MediaAgent using dedicated OpenAI client for images")
            except Exception as e:
                if self.logger:
                    self.logger.log_error(error=e, context="MediaAgent image client creation")
                # Fall back to main client (may fail but graceful degradation)
                image_client = client

        self.image_generator = ImageGenerator(image_client, default_model)

    def create_images(self, topic, subject, grade, style="educational", language="English", n=1, 
                      model_name=None, custom_prompt=None) -> List[Dict[str, Optional[str]]]:
        """Delegate image generation to ImageGenerator for consistency
        
        Args:
            topic: The topic to generate images for
            subject: The subject area
            grade: The grade level
            style: The teaching style
            language: The language
            n: Number of images to generate
            model_name: Optional model name override
            custom_prompt: Optional custom prompt that takes precedence over the template
            
        Returns:
            List of dictionaries with image data
        """
        if not topic:
            return []

        # If images are disabled (e.g., non-OpenAI provider with no OPENAI_API_KEY),
        # skip image generation entirely to avoid noisy authentication errors.
        if not self.images_enabled:
            return []

        # Use the custom prompt if provided, otherwise generate from template
        if custom_prompt:
            prompt = custom_prompt
            print(f"Using custom image prompt based on lesson content analysis")
        else:
            prompt = self.prompt_template.format(
                topic=topic, subject=subject, grade=grade, style=style, language=language
            )
            print(f"Using standard template-based image prompt")
        
        # Get image size from config if available
        config_size = self.config["defaults"].get("image_size") if self.config and "defaults" in self.config else None
        
        # Delegate to ImageGenerator for actual image creation
        return self.image_generator.create_image(
            prompt=prompt,
            model=model_name,
            size=config_size,
            n=n,
            topic=topic,
            subject=subject,
            grade=grade,
            style=style,
            language=language
        )


class ChartAgent(BaseAgent):
    """Agent responsible for generating chart suggestions and visualizations"""
    
    def __init__(self, client, model, config):
        super().__init__(client, model)
        self.prompt_template = config["prompts"].get("chart", "")
    
    def suggest_chart(self, topic, subject, grade, style, language) -> Optional[Dict[str, Any]]:
        prompt = self.prompt_template.format(
            topic=topic, subject=subject, grade=grade, style=style, language=language
        )
        
        try:
            response = self._call_model(
                [{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            if response and response.choices:
                content = response.choices[0].message.content
                try:
                    data = json.loads(content)
                    # Add the suggestion text for reference
                    data["suggestion_text"] = f"Chart type: {data.get('chart_type', 'unknown')}, Title: {data.get('title', 'untitled')}"
                    return data
                except json.JSONDecodeError:
                    print(f"Chart JSON decode error: {content}")
            return None
        except Exception as e:
            print(f"Chart suggestion error: {e}")
            return None
    
    def create_chart(self, chart_info: Optional[Dict[str, Any]], use_plotly: bool = True) -> Optional[Dict[str, Any]]:
        """Creates a chart using Plotly (preferred) or Matplotlib (fallback).
        
        Args:
            chart_info: Chart configuration dict with chart_type, title, data, labels, etc.
            use_plotly: If True, generate Plotly JSON. If False or on error, use matplotlib.
            
        Returns:
            Dict with either:
                - Plotly: {"plotly_config": {...}, "title": str, "chart_type": "plotly"}
                - Matplotlib: {"b64": str, "title": str, "chart_type": "matplotlib"}
                - None on total failure
        """
        if not chart_info:
            return None

        # Safely extract data with defaults
        chart_type = chart_info.get("chart_type", "Bar").capitalize()
        title = chart_info.get("title", "Generated Chart")
        data = chart_info.get("data", {})
        labels = data.get("labels", [])
        values = data.get("values", [])
        x_label = chart_info.get("x_label", "")
        y_label = chart_info.get("y_label", "Values")

        # Validation before plotting
        if not labels or not values:
            error_msg = f"Cannot create chart '{title}': Missing labels or values."
            print(error_msg)
            try:
                import streamlit as st
                st.warning(f"Chart generation issue: {error_msg}")
            except ImportError:
                pass
            return None

        # Convert values to numeric
        try:
            numeric_values = []
            for v in values:
                try:
                    numeric_values.append(float(v))
                except (ValueError, TypeError):
                    numeric_values.append(0.1)
                    print(f"Warning: Non-numeric value '{v}' in chart data, using placeholder.")
        except Exception as e:
            error_msg = f"Cannot create chart '{title}': Values contain non-numeric data ({values}). Error: {e}"
            print(error_msg)
            return None

        # Try Plotly first if requested
        if use_plotly:
            try:
                plotly_config = self._create_plotly_chart(
                    chart_type, title, labels, numeric_values, x_label, y_label
                )
                if plotly_config:
                    return {
                        "plotly_config": plotly_config,
                        "title": title,
                        "chart_type": "plotly"
                    }
            except Exception as e:
                print(f"Plotly chart generation failed, falling back to matplotlib: {e}")
                # Continue to matplotlib fallback

        # Matplotlib fallback
        return self._create_matplotlib_chart(
            chart_type, title, labels, numeric_values, x_label, y_label
        )
    
    def _create_plotly_chart(self, chart_type: str, title: str, labels: List, 
                            values: List[float], x_label: str, y_label: str) -> Optional[Dict]:
        """Generate Plotly chart configuration.
        
        Returns:
            Dict compatible with plotly.graph_objects or None on failure
        """
        try:
            # Import plotly here to make it optional
            import plotly.graph_objects as go
            
            # Adjust values for pie charts (must be positive)
            if chart_type == "Pie":
                values = [max(0.1, abs(v)) for v in values]
                if all(v == 0 for v in values):
                    values = [1] * len(values)
            
            # Create the appropriate trace based on chart type
            if chart_type == "Bar":
                trace = go.Bar(
                    x=labels,
                    y=values,
                    text=[str(v) for v in values],
                    textposition='outside',
                    marker=dict(color='rgb(55, 128, 191)')
                )
                layout = go.Layout(
                    title=title,
                    xaxis=dict(title=x_label),
                    yaxis=dict(title=y_label),
                    hovermode='closest'
                )
                
            elif chart_type == "Line":
                trace = go.Scatter(
                    x=labels,
                    y=values,
                    mode='lines+markers+text',
                    text=[str(v) for v in values],
                    textposition='top center',
                    marker=dict(size=10, color='rgb(34, 139, 34)'),
                    line=dict(width=2)
                )
                layout = go.Layout(
                    title=title,
                    xaxis=dict(title=x_label),
                    yaxis=dict(title=y_label),
                    hovermode='closest'
                )
                
            elif chart_type == "Pie":
                trace = go.Pie(
                    labels=labels,
                    values=values,
                    textposition='inside',
                    textinfo='label+percent',
                    hoverinfo='label+value+percent',
                    marker=dict(line=dict(color='white', width=2))
                )
                layout = go.Layout(
                    title=title
                )
                
            else:
                # Default to bar chart for unknown types
                trace = go.Bar(
                    x=labels,
                    y=values,
                    text=[str(v) for v in values],
                    textposition='outside',
                    marker=dict(color='rgb(55, 128, 191)')
                )
                layout = go.Layout(
                    title=title,
                    xaxis=dict(title=x_label),
                    yaxis=dict(title=y_label),
                    hovermode='closest'
                )
            
            # Create figure
            fig = go.Figure(data=[trace], layout=layout)
            
            # Return the figure as a dict that can be used with st.plotly_chart()
            return fig.to_dict()
            
        except ImportError:
            print("Plotly not available, falling back to matplotlib")
            return None
        except Exception as e:
            print(f"Error creating Plotly chart: {e}")
            return None
    
    def _create_matplotlib_chart(self, chart_type: str, title: str, labels: List,
                                 values: List[float], x_label: str, y_label: str) -> Optional[Dict]:
        """Generate matplotlib chart as base64 PNG (fallback method).
        
        Returns:
            Dict with {"b64": str, "title": str, "chart_type": "matplotlib"} or None
        """
        # Check if matplotlib is available
        if not MATPLOTLIB_AVAILABLE:
            print("Cannot create chart: matplotlib is not installed.")
            try:
                import streamlit as st
                st.warning("Chart generation requires matplotlib which is not installed.")
            except ImportError:
                pass
            return {"title": title, "b64": None, "error": "matplotlib not installed", "chart_type": "matplotlib"}

        fig = None
        try:
            fig, ax = plt.subplots(figsize=(6, 4))

            # For pie charts, ensure all values are positive
            if chart_type == "Pie":
                values = [max(0.1, abs(v)) for v in values]

            if chart_type == "Bar":
                ax.bar(labels, values, color='skyblue')
                ax.set_xlabel(x_label)
                ax.set_ylabel(y_label)
                # Add value labels on top of bars
                for i, v in enumerate(values):
                    ax.text(i, v, str(v), ha='center', va='bottom')
                    
            elif chart_type == "Line":
                ax.plot(labels, values, marker='o', linestyle='-', color='green')
                ax.set_xlabel(x_label)
                ax.set_ylabel(y_label)
                # Add data point labels
                for i, v in enumerate(values):
                    ax.text(i, v, str(v), ha='center', va='bottom')
                    
            elif chart_type == "Pie":
                try:
                    # Handle case where all values are 0
                    if all(v == 0 for v in values):
                        values = [1] * len(values)
                    
                    ax.pie(values, labels=labels, autopct='%1.1f%%', 
                           shadow=True, startangle=90)
                    ax.axis('equal')
                except Exception as pie_error:
                    print(f"Error with pie chart, falling back to bar: {pie_error}")
                    ax.clear()
                    ax.bar(labels, values, color='skyblue')
                    ax.set_xlabel(x_label)
                    ax.set_ylabel(y_label)
            else:
                # Default to bar chart if unrecognized type
                ax.bar(labels, values, color='skyblue')
                ax.set_xlabel(x_label)
                ax.set_ylabel(y_label)

            ax.set_title(title)
            plt.tight_layout()

            # Save to bytes
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            plt.close(fig)

            # Convert to base64
            image_b64 = base64.b64encode(buffer.read()).decode('utf-8')
            
            return {"b64": image_b64, "title": title, "chart_type": "matplotlib"}

        except Exception as e:
            error_msg = f"Error creating matplotlib chart: {e}"
            print(error_msg)
            if fig:
                plt.close(fig)
            
            try:
                import streamlit as st
                st.warning(f"Chart generation issue: {error_msg}")
            except ImportError:
                pass
                
            return None


class QuizAgent(BaseAgent):
    """Agent responsible for generating quiz questions"""
    
    def __init__(self, client, model, config):
        super().__init__(client, model)
        self.prompt_template = config["prompts"].get("quiz", "")
    
    def generate_quiz(self, topic, subject, grade, style, language) -> Optional[List[Dict[str, Any]]]:
        prompt = self.prompt_template.format(
            topic=topic, subject=subject, grade=grade, style=style, language=language
        )
        
        try:
            response = self._call_model(
                [{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            if response and response.choices:
                content = response.choices[0].message.content
                try:
                    data = json.loads(content)
                    return data.get("quiz", [])
                except json.JSONDecodeError:
                    print(f"Quiz JSON decode error: {content}")
            return None
        except Exception as e:
            print(f"Quiz generation error: {e}")
            return None


class SummaryAgent(BaseAgent):
    """Agent responsible for generating lesson summaries"""
    
    def __init__(self, client, model, config):
        super().__init__(client, model)
        self.prompt_template = config["prompts"].get("summary", "")
    
    def generate_summary(self, topic, subject, grade, language) -> str:
        prompt = self.prompt_template.format(
            topic=topic or "[Topic Missing]",
            subject=subject or "[Subject Missing]",
            grade=grade or "[Grade Missing]",
            language=language or "English"
        )
        
        try:
            response = self._call_model(
                [{"role": "system", "content": prompt}],
                temperature=0.7
            )
            
            if response and response.choices:
                return response.choices[0].message.content
            return ""
        except Exception as e:
            print(f"Summary generation error: {e}")
            return ""


class ResourceAgent(BaseAgent):
    """Agent responsible for suggesting further resources"""
    
    def __init__(self, client, model, config):
        super().__init__(client, model)
        self.prompt_template = config["prompts"].get("resources", "")
    
    def generate_resources(self, topic, subject, grade, language) -> str:
        prompt = self.prompt_template.format(
            topic=topic or "[Topic Missing]",
            subject=subject or "[Subject Missing]",
            grade=grade or "[Grade Missing]",
            language=language or "English"
        )
        
        try:
            response = self._call_model(
                [{"role": "system", "content": prompt}],
                temperature=0.7
            )
            
            if response and response.choices:
                return response.choices[0].message.content
            return ""
        except Exception as e:
            print(f"Resources generation error: {e}")
            return ""


class ImagePromptAgent(BaseAgent):
    """Agent that analyzes lesson content and generates tailored image prompts"""
    
    def __init__(self, client, model, config=None):
        super().__init__(client, model)
        # Default prompt if not in config
        self.default_prompt = """
        You are an expert at creating educational image prompts that perfectly match lesson content.
        
        You'll be given a lesson about "{topic}" in {subject} for grade {grade} students.
        
        Your task is to:
        1. Analyze the specific concepts, examples, and explanations in the lesson
        2. Identify the most important visual elements that would enhance understanding
        3. Create a detailed, specific image prompt (200-250 words) that would generate an illustration
           directly supporting this exact lesson content - not just the general topic
        
        Important:
        - Focus on the specific content actually mentioned in the lesson, not general knowledge about the topic
        - Be concrete and detailed, describing specific elements that should appear in the image
        - Include age-appropriate complexity for grade {grade} students
        - Incorporate the lesson's teaching style: {style}
        - Consider cultural context for: {language}
        - Include colors, composition details, and mood of the image
        
        Your prompt should produce an image that:
        - Directly supports the learning objectives in the content
        - Visualizes the most difficult or abstract concept from the lesson
        - Would make sense to a student after reading this exact lesson
        """
    
    def create_image_prompt(self, content, topic, subject, grade, style, language) -> str:
        """Analyze content and create a tailored image prompt
        
        Args:
            content: The lesson content to analyze
            topic: The topic title
            subject: The subject
            grade: The grade level
            style: The teaching style
            language: The language
            
        Returns:
            str: A detailed image prompt based on the content
        """
        # Format the system prompt with metadata
        system_prompt = self.default_prompt.format(
            topic=topic or "[Topic Missing]",
            subject=subject or "[Subject Missing]",
            grade=grade or "[Grade Missing]",
            style=style or "[Style Missing]",
            language=language or "English"
        )
        
        # Create a user prompt with the content to analyze
        user_prompt = f"""
        TOPIC: {topic}
        SUBJECT: {subject}
        GRADE: {grade}
        
        LESSON CONTENT TO ANALYZE:
        {content[:3000]}  # Use first 3000 chars for analysis
        
        Based on this specific lesson content, create a detailed, education-focused image prompt that would 
        generate an illustration perfectly matched to what students are learning in this text.
        """
        
        try:
            # Make the API call
            response = self._call_model(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            
            # Process the response
            if response and response.choices:
                custom_prompt = response.choices[0].message.content
                
                # Log for debugging
                if self.logger:
                    self.logger.log_debug(f"Generated custom image prompt: {custom_prompt[:100]}...")
                print(f"Generated custom image prompt based on lesson content: {custom_prompt[:100]}...")
                
                return custom_prompt
            
            # Fallback if API call fails
            return None
        except Exception as e:
            print(f"Image prompt generation error: {e}")
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Image prompt generation")
            return None
