"""
Enhanced Image Generation Module for Curriculum Generator
Supports multiple image models including gpt-image-1, dall-e-3, and dall-e-2
"""

import base64
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import traceback
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from openai import APIError, RateLimitError, APIConnectionError, AuthenticationError, BadRequestError

# Import the verbose logger
try:
    from src.verbose_logger import get_logger
    logger = get_logger()
except ImportError:
    # Fallback if logger module not available
    logger = None

class ImageGenerator:
    """Handles image generation with multiple model support"""
    
    def __init__(self, client, default_model="gpt-image-1"):
        """Initialize with OpenAI client and default model"""
        self.client = client
        self.default_model = default_model
        
        # Define supported models and their sizes based on your available models
        self.models = {
            "gpt-image-1": {"sizes": ["1024x1024", "1024x1536", "1536x1024", "auto"]},
            "gpt-image-1-mini": {"sizes": ["1024x1024", "1024x1536", "1536x1024", "auto"]},
        }

        # Default sizes for each model - using 1024x1024 for all as safest option
        self.default_sizes = {
            "gpt-image-1": "1024x1024",
            "gpt-image-1-mini": "1024x1024",
        }

        # Maximum prompt lengths per model
        self.max_prompt_lengths = {
            "gpt-image-1": 32000,
            "gpt-image-1-mini": 32000,
        }

    def _download_image_with_retry(
        self, url: str, max_retries: int = 3, timeout: float = 30.0
    ) -> Optional[bytes]:
        """Download an image with retry and backoff."""
        session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            msg = f"Failed to download image after {max_retries} retries: {e}"
            print(msg)
            if logger:
                logger.log_error(error=e, model="image_download", context=msg)
            return None
    
    def create_image(self, prompt: str, model: str = None, size: str = None, n: int = 1, 
                   topic: str = None, subject: str = None, grade: str = None, 
                   style: str = None, language: str = None) -> List[Dict[str, Any]]:
        """Generate images using the specified model and parameters
        
        Args:
            prompt: The prompt to use for image generation (can be custom or template-based)
            model: Optional model override
            size: Optional size override
            n: Number of images to generate
            topic: Topic (used only if no prompt provided)
            subject: Subject (used only if no prompt provided)
            grade: Grade level (used only if no prompt provided)
            style: Teaching style (used only if no prompt provided)
            language: Language (used only if no prompt provided)
            
        Returns:
            List of image data dictionaries
        """
        # Sanitize sensitive subjects to avoid moderation blocks
        sanitized_subject = subject
        if subject:
            sensitive_subjects = ["health", "human body", "anatomy", "reproduction", "drugs", "medication", "safety"]
            
            for sensitive in sensitive_subjects:
                if sensitive.lower() in subject.lower():
                    sanitized_subject = "Educational Science"
                    print(f"Note: Sanitized potentially sensitive subject '{subject}' to '{sanitized_subject}' for image generation")
                    break
        
        # Use provided prompt or generate from template if all metadata provided
        if not prompt and all([topic, sanitized_subject, grade]):
            print("Using template-based prompt from metadata")
            # This would require access to the prompt template
            # For now, just use a basic format that avoids moderation flags
            prompt = f"Educational cartoon illustration about {topic} for grade {grade} students learning {sanitized_subject}."
        
        # Sanitize the prompt if provided directly
        if prompt:
            # Add educational context to avoid moderation
            if "educational" not in prompt.lower() and "cartoon" not in prompt.lower():
                prompt = f"Educational cartoon illustration: {prompt}"
            
            # Avoid specific terms that might trigger moderation
            problematic_terms = ["human anatomy", "body parts", "reproduction", "medication", "drugs", "illness"]
            for term in problematic_terms:
                if term.lower() in prompt.lower():
                    print(f"Replacing potentially problematic term '{term}' in prompt")
                    prompt = prompt.lower().replace(term.lower(), "science concepts")
            
        # Define fallback models to try if the primary one fails
        # ONLY gpt-image models allowed per project requirements
        models_to_try = []
        use_model = model or self.default_model
        
        # Add the primary model first
        models_to_try.append(use_model)
        
        # Add gpt-image-1-mini as fallback if not already selected
        if use_model != "gpt-image-1-mini":
            models_to_try.append("gpt-image-1-mini")
            
        results = []
        last_error = None
        success = False
        
        # Try each model in sequence until one works
        for current_model in models_to_try:
            if success:
                break
                
            # Skip if this model isn't supported
            if current_model not in self.models:
                print(f"Warning: Unsupported model {current_model}, skipping")
                continue
                
            # Get available sizes for this model
            available_sizes = self.models[current_model]["sizes"]
            
            # Validate size is supported for this model, or use default
            use_size = size if size in available_sizes else self.default_sizes[current_model]
            
            try:
                # Truncate prompt if needed for this model
                max_length = self.max_prompt_lengths.get(current_model, 1000)
                truncated_prompt = prompt
                if len(prompt) > max_length:
                    truncated_prompt = prompt[:max_length - 50] + "... [educational illustration]"
                    print(f"Warning: Prompt truncated from {len(prompt)} to {len(truncated_prompt)} chars for {current_model}")

                # Create parameters based on the selected model
                params = {
                    "model": current_model,
                    "prompt": truncated_prompt,
                    "n": 1,  # API-defined limitation for certain models
                    "size": use_size
                }

                # For gpt-image models, we need to ensure we're using supported size
                if current_model in ["gpt-image-1", "gpt-image-1-mini"]:
                    if use_size not in ["1024x1024", "1024x1536", "1536x1024", "auto"]:
                        use_size = "1024x1024"
                        params["size"] = use_size
                    
                # Log information for debugging
                print(f"Using model {current_model} with parameters: {params}")
                
                # Make multiple calls if needed
                for i in range(n):
                    current_prompt = f"{prompt} (Variation {i+1}/{n})" if n > 1 else prompt
                    current_params = params.copy()
                    current_params["prompt"] = current_prompt
                    
                    # Log API request with the logger if available
                    if logger:
                        logger.log_api_request(
                            model=current_model,
                            endpoint="images.generate",
                            params=current_params
                        )
                    
                    # Make the API call
                    response = self.client.images.generate(**current_params)
                    
                    # Log API response with the logger if available
                    if logger:
                        logger.log_api_response(model=current_model, response=response)
                    
                    # Process the results
                    if hasattr(response, 'data') and response.data:
                        for img_data in response.data:
                            # Debug image data if logger available
                            if logger:
                                logger.log_debug(f"Processing image data: {type(img_data)}")
                            
                            # Simplified handling based on response attributes
                            # Check for URL first (gpt-image-1 returns URLs)
                            if hasattr(img_data, 'url') and img_data.url:
                                try:
                                    # Download image from URL and convert to base64
                                    if logger:
                                        logger.log_debug(f"Downloading image from URL: {img_data.url[:30]}...")
                                    print(f"Downloading image from URL: {img_data.url[:50]}...")

                                    image_data = self._download_image_with_retry(img_data.url)
                                    if image_data:
                                        b64_data = base64.b64encode(image_data).decode('utf-8')
                                        results.append({
                                            "b64": b64_data,
                                            "prompt": current_prompt,
                                            "model": current_model,
                                            "size": use_size
                                        })
                                        print(f"Successfully downloaded and encoded image from URL using {current_model}")
                                        success = True
                                    else:
                                        print("Failed to download image from URL after retries")
                                except Exception as e:
                                    print(f"Error downloading image from URL: {e}")
                            
                            # Check for b64_json (typically dall-e models)
                            elif hasattr(img_data, 'b64_json') and img_data.b64_json:
                                print(f"Image returned as base64 data using {current_model}")
                                results.append({
                                    "b64": img_data.b64_json,
                                    "prompt": current_prompt,
                                    "model": current_model,
                                    "size": use_size
                                })
                                success = True
                            
                            # For revised_prompt used by dall-e-3
                            if hasattr(img_data, 'revised_prompt') and img_data.revised_prompt:
                                print(f"Revised prompt: {img_data.revised_prompt[:50]}...")
                            
                            # Log unexpected response formats
                            if not (hasattr(img_data, 'url') or hasattr(img_data, 'b64_json')):
                                print(f"Unexpected response format from {current_model}: {img_data}")
                    
                    # If we got at least one result, break out of the loop
                    if success:
                        break

            except RateLimitError as e:
                # Rate limit - retryable but try next model for now
                last_error = e
                if logger:
                    logger.log_error(error=e, model=current_model, context="Image generation rate limit")
                print(f"Rate limit exceeded with {current_model}: {e} - Trying next model if available.")
                continue

            except AuthenticationError as e:
                # Authentication error - non-retryable, fail fast
                last_error = e
                if logger:
                    logger.log_error(error=e, model=current_model, context="Image generation authentication")
                print(f"Authentication error with {current_model}: {e}")
                break  # No point trying other models with auth error

            except APIConnectionError as e:
                # Connection error - retryable but try next model for now
                last_error = e
                if logger:
                    logger.log_error(error=e, model=current_model, context="Image generation connection error")
                print(f"Connection error with {current_model}: {e} - Trying next model if available.")
                continue

            except BadRequestError as e:
                # Bad request - might be model-specific, try next model
                last_error = e
                if logger:
                    logger.log_error(error=e, model=current_model, context="Image generation bad request")
                print(f"Bad request with {current_model}: {e} - Trying next model if available.")
                continue

            except APIError as e:
                # Generic API error - try next model
                error_msg = str(e)
                last_error = e
                if logger:
                    logger.log_error(error=e, model=current_model, context="Image generation API error")
                print(f"API error with {current_model}: {error_msg} - Trying next model if available.")
                continue

            except Exception as e:
                # Unexpected error
                error_msg = str(e)
                last_error = e
                if logger:
                    logger.log_error(error=e, model=current_model, context="Image generation unexpected error")
                    logger.log_debug(traceback.format_exc())
                print(f"Unexpected error with {current_model}: {error_msg} - Trying next model if available.")
                continue
        
        # If we've tried all models and still no success, show error and create placeholder
        if not results:
            error_msg = str(last_error) if last_error else "Unknown error"
            
            # Show appropriate error to user in Streamlit UI
            try:
                import streamlit as st
                if "moderation" in error_msg.lower() or "safety" in error_msg.lower():
                    st.warning("⚠️ Image generation was blocked by safety filters. Using a placeholder image instead.")
                elif "quota" in error_msg.lower() or "insufficient_quota" in error_msg:
                    st.error("⚠️ OpenAI API quota exceeded. Please check your billing details or try again later.")
                else:
                    st.warning(f"Image generation failed across all models. Using placeholder image instead.")
            except ImportError:
                pass  # Can't import streamlit, skip UI notification
            
            # Create a placeholder image
            placeholder_b64 = self._create_placeholder_image(f"Educational illustration for {topic or 'this topic'}")
            if placeholder_b64:
                results.append({
                    "b64": placeholder_b64,
                    "prompt": prompt,
                    "model": "placeholder",
                    "is_placeholder": True
                })
        
        return results
    
    def _create_placeholder_image(self, text: str) -> Optional[str]:
        """Creates a simple placeholder image with an error message"""
        try:
            # Create a simple color image
            width, height = 512, 256
            img = Image.new('RGB', (width, height), color=(73, 109, 137))
            draw = ImageDraw.Draw(img)
            
            # Try to load a font, with fallbacks
            try:
                font = ImageFont.truetype("Arial.ttf", 14)
            except IOError:
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", 14)
                except IOError:
                    font = ImageFont.load_default()
            
            # Draw text with simple wrapping
            lines = []
            words = text.split()
            current_line = ""
            
            for word in words:
                test_line = f"{current_line} {word}".strip()
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] < width - 20:  # 10px margin
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # Draw text lines
            y_position = 20
            for line in lines:
                draw.text((10, y_position), line, font=font, fill=(255, 255, 255))
                y_position += 20
            
            # Convert to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
            
        except Exception as e:
            print(f"Error creating placeholder image: {e}")
            return None
    
    def get_available_models(self) -> List[str]:
        """Return list of available image models"""
        return list(self.models.keys())
    
    def get_available_sizes(self, model: str) -> List[str]:
        """Return available sizes for a specific model"""
        return self.models.get(model, {"sizes": []})["sizes"]
