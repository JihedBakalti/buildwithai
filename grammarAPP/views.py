from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .forms import GrammarCheckForm
import google.generativeai as genai
import json
import re

@login_required(login_url='index')
def grammar_helper(request):
    """Grammar helper page with Google Gemini API integration"""
    form = GrammarCheckForm()
    results = None
    original_text = None
    
    if request.method == 'POST':
        form = GrammarCheckForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Get text from form
                text_to_check = form.get_text()
                original_text = text_to_check
                
                if not text_to_check.strip():
                    messages.error(request, 'Please provide some text to check.')
                else:
                    # Configure Gemini API
                    genai.configure(api_key=settings.GEMINI_API_KEY)
                    
                    # Create structured prompt
                    prompt = f"""You are an expert English grammar and writing assistant. Analyze the following text and provide a comprehensive grammar check.

TEXT TO CHECK:
{text_to_check}

Please provide your analysis in the following JSON format:
{{
    "corrected_text": "The fully corrected version of the text",
    "errors": [
        {{
            "original": "the incorrect phrase or sentence",
            "corrected": "the corrected version",
            "explanation": "brief explanation of the error",
            "error_type": "grammar/spelling/punctuation/style"
        }}
    ],
    "overall_score": 85,
    "suggestions": [
        "General suggestion for improvement",
        "Another suggestion"
    ],
    "summary": "Brief summary of the main issues found and overall quality"
}}

IMPORTANT: Return ONLY valid JSON, no additional text before or after."""

                    # Try different model names in order of preference
                    # Updated for free tier available models
                    model_names = [
                        'models/gemini-2.5-flash',  # Fastest and most cost-effective
                        'models/gemini-2.5-pro',    # Best quality
                        'models/gemini-2.5-pro-preview-06-05',
                        'models/gemini-2.5-pro-preview-05-06',
                        'models/gemini-2.5-pro-preview-03-25',
                        # Fallback to older models if available
                        'models/gemini-pro',
                        'gemini-pro',
                    ]
                    model = None
                    response = None
                    last_error = None
                    
                    for model_name in model_names:
                        try:
                            model = genai.GenerativeModel(model_name)
                            # Configure safety settings to allow more content
                            safety_settings = [
                                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                            ]
                            # Call Gemini API
                            response = model.generate_content(
                                prompt,
                                generation_config={
                                    'temperature': 0.3,
                                    'max_output_tokens': 2000,
                                },
                                safety_settings=safety_settings
                            )
                            break  # Success, exit loop
                        except Exception as e:
                            last_error = str(e)
                            # Continue to next model
                            continue
                    
                    if not response:
                        # If all models failed, try to list available models for debugging
                        try:
                            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                            error_msg = f"Failed to use any available model. Last error: {last_error}. Available models: {', '.join(available_models[:5])}"
                        except:
                            error_msg = f"Failed to use any available model. Last error: {last_error}. Please check your API key."
                        raise Exception(error_msg)
                    
                    # Check if response was blocked or filtered
                    if response.candidates and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'finish_reason') and candidate.finish_reason == 2:
                            raise Exception("Content was blocked by safety filters. Please try with different text.")
                        if hasattr(candidate, 'finish_reason') and candidate.finish_reason != 1:
                            raise Exception(f"Response was not completed. Finish reason: {candidate.finish_reason}")
                    
                    # Extract response
                    try:
                        response_text = response.text.strip()
                    except AttributeError:
                        # If response.text doesn't work, try accessing parts directly
                        if response.candidates and len(response.candidates) > 0:
                            candidate = response.candidates[0]
                            if candidate.content and candidate.content.parts:
                                response_text = ''.join([part.text for part in candidate.content.parts if hasattr(part, 'text')]).strip()
                            else:
                                raise Exception("Response does not contain valid content.")
                        else:
                            raise Exception("No candidates in response.")
                    
                    # Try to extract JSON from response (in case there's extra text)
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(0)
                    
                    # Parse JSON response
                    try:
                        results = json.loads(response_text)
                    except json.JSONDecodeError:
                        # If JSON parsing fails, create a fallback response
                        results = {
                            "corrected_text": response_text,
                            "errors": [],
                            "overall_score": 0,
                            "suggestions": ["Could not parse response. Showing raw output."],
                            "summary": "Response received but could not be parsed into structured format."
                        }
                        messages.warning(request, 'Received response but had trouble parsing it. Showing raw output.')
                    
                    messages.success(request, 'Grammar check completed successfully!')
                    
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
                results = None
    
    # Debug: Log form errors if form is invalid
    if request.method == 'POST' and not form.is_valid():
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
    
    context = {
        'form': form,
        'results': results,
        'original_text': original_text,
    }
    return render(request, 'grammarAPP/grammar.html', context)
