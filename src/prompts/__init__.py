"""
Prompt templates for DeepSeek API.
Advanced prompt engineering techniques:
- Multi-shot prompting (few-shot examples)
- Chain-of-Thought (CoT) reasoning
- Role-based prompting
- Temperature optimization
- Token budgeting
"""

from enum import Enum
from typing import Dict, List, Optional, Any
import json


class TaskType(str, Enum):
    """Types of tasks for prompt engineering"""
    SEO_ARTICLE = "seo_article"
    TRANSLATION = "translation"
    CONTENT_CREATION = "content_creation"
    CODE_GENERATION = "code_generation"
    SOCIAL_MEDIA = "social_media"
    COPYWRITING = "copywriting"
    SUMMARIZATION = "summarization"
    ANALYSIS = "analysis"


class PromptVersion(str, Enum):
    """Prompt versions for A/B testing"""
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"


class PromptTemplate:
    """Base class for prompt templates"""
    
    def __init__(self, task_type: TaskType, version: PromptVersion = PromptVersion.V1):
        self.task_type = task_type
        self.version = version
        self.temperature = self._get_temperature()
        self.max_tokens = self._get_max_tokens()
    
    def _get_temperature(self) -> float:
        """Get temperature based on task type"""
        temperatures = {
            TaskType.SEO_ARTICLE: 0.5,
            TaskType.TRANSLATION: 0.3,
            TaskType.CONTENT_CREATION: 0.7,
            TaskType.CODE_GENERATION: 0.2,
            TaskType.SOCIAL_MEDIA: 0.8,
            TaskType.COPYWRITING: 0.6,
            TaskType.SUMMARIZATION: 0.4,
            TaskType.ANALYSIS: 0.5,
        }
        return temperatures.get(self.task_type, 0.7)
    
    def _get_max_tokens(self) -> int:
        """Get max tokens based on task type"""
        max_tokens = {
            TaskType.SEO_ARTICLE: 2000,
            TaskType.TRANSLATION: 1000,
            TaskType.CONTENT_CREATION: 1500,
            TaskType.CODE_GENERATION: 3000,
            TaskType.SOCIAL_MEDIA: 500,
            TaskType.COPYWRITING: 1000,
            TaskType.SUMMARIZATION: 800,
            TaskType.ANALYSIS: 1200,
        }
        return max_tokens.get(self.task_type, 1500)
    
    def get_system_prompt(self) -> str:
        """Get system prompt based on task type and version"""
        raise NotImplementedError
    
    def get_examples(self) -> List[Dict[str, str]]:
        """Get few-shot examples for the task"""
        raise NotImplementedError
    
    def build_prompt(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """Build complete prompt with system message and examples"""
        system_prompt = self.get_system_prompt()
        examples = self.get_examples()
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add few-shot examples if available
        for example in examples:
            if "user" in example and "assistant" in example:
                messages.append({"role": "user", "content": example["user"]})
                messages.append({"role": "assistant", "content": example["assistant"]})
        
        # Add user input
        enhanced_input = self._enhance_user_input(user_input, **kwargs)
        messages.append({"role": "user", "content": enhanced_input})
        
        return {
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "task_type": self.task_type.value,
            "version": self.version.value,
        }
    
    def _enhance_user_input(self, user_input: str, **kwargs) -> str:
        """Enhance user input with task-specific instructions"""
        return user_input


class SEOArticlePrompt(PromptTemplate):
    """Prompt template for SEO article writing"""
    
    def __init__(self, version: PromptVersion = PromptVersion.V1):
        super().__init__(TaskType.SEO_ARTICLE, version)
    
    def get_system_prompt(self) -> str:
        if self.version == PromptVersion.V1:
            return """You are an expert SEO content writer with 10+ years of experience.
Your task is to create high-quality, SEO-optimized articles that rank well in search engines.

CRITERIA:
1. Keyword optimization: Use target keywords naturally (2-3% density)
2. Structure: Clear H1, H2, H3 headings with logical flow
3. Readability: Flesch-Kincaid score > 60, short paragraphs (3-4 sentences)
4. Engagement: Hook readers in first paragraph, include CTAs
5. Originality: 100% unique content, no plagiarism
6. Length: 1500-2000 words for comprehensive coverage

FORMAT:
- Meta Title: 50-60 characters with primary keyword
- Meta Description: 150-160 characters with keywords
- Introduction: Problem statement + promise
- Body: 3-5 sections with H2 headings
- Conclusion: Summary + next steps
- Call-to-Action: Clear, actionable next step

Think step by step:
1. Analyze the topic and target keywords
2. Research competitor articles
3. Outline the structure
4. Write engaging, informative content
5. Optimize for SEO and readability"""
        
        elif self.version == PromptVersion.V2:
            return """You are a data-driven SEO specialist. Create articles based on SERP analysis and user intent.

APPROACH:
1. Search Intent: Identify informational, commercial, or transactional intent
2. SERP Features: Target featured snippets, "People also ask", related searches
3. E-E-A-T: Demonstrate Experience, Expertise, Authoritativeness, Trustworthiness
4. Semantic SEO: Use related terms, synonyms, and LSI keywords
5. Mobile-First: Optimize for mobile devices (short paragraphs, clear headings)

TECHNICAL SEO:
- URL structure: Clean, keyword-rich
- Internal linking: 2-3 relevant internal links
- External references: Cite authoritative sources
- Schema markup: Consider Article, HowTo, FAQ schemas

Write in a conversational yet authoritative tone."""
        
        return self.get_system_prompt()  # Default to V1
    
    def get_examples(self) -> List[Dict[str, str]]:
        return [
            {
                "user": "Write an SEO article about 'best running shoes for flat feet' with keywords: running shoes, flat feet, arch support, stability shoes",
                "assistant": """Meta Title: Best Running Shoes for Flat Feet 2024 | Top Arch Support & Stability
Meta Description: Discover the best running shoes for flat feet with superior arch support and stability. Our expert review covers top brands, features, and buying guide.

# Best Running Shoes for Flat Feet: Ultimate Guide for Runners

## Introduction
For runners with flat feet, finding the right shoes isn't just about comfort—it's about injury prevention. Flat feet (pes planus) lack natural arch support, leading to overpronation and increased stress on knees, hips, and back. This comprehensive guide reviews the best running shoes for flat feet, focusing on arch support, stability features, and proper fit.

## Understanding Flat Feet and Running Mechanics
Flat feet occur when the arches don't develop properly or collapse over time...

[Article continues with 1500+ words of detailed content]"""
            }
        ]
    
    def _enhance_user_input(self, user_input: str, **kwargs) -> str:
        keywords = kwargs.get("keywords", "")
        word_count = kwargs.get("word_count", 1500)
        tone = kwargs.get("tone", "professional")
        
        enhanced = f"""TOPIC: {user_input}

REQUIREMENTS:
- Target keywords: {keywords}
- Word count: {word_count} words
- Tone: {tone}
- Include: Meta title, meta description, introduction, 3-5 body sections, conclusion, call-to-action

Please create a comprehensive SEO article following the system instructions."""
        
        return enhanced


class TranslationPrompt(PromptTemplate):
    """Prompt template for translation tasks"""
    
    def __init__(self, version: PromptVersion = PromptVersion.V1):
        super().__init__(TaskType.TRANSLATION, version)
    
    def get_system_prompt(self) -> str:
        return """You are a professional translator with native-level proficiency in multiple languages.
Your translations must be accurate, natural-sounding, and culturally appropriate.

TRANSLATION PRINCIPLES:
1. Accuracy: Preserve original meaning without adding or omitting content
2. Naturalness: Use idiomatic expressions appropriate for target language
3. Consistency: Maintain consistent terminology throughout
4. Cultural adaptation: Adjust cultural references when necessary
5. Tone preservation: Match formal/informal tone of original
6. Context awareness: Consider surrounding text and purpose

SPECIAL CASES:
- Technical terms: Research industry-standard translations
- Proper nouns: Use established translations or transliterate
- Idioms: Find equivalent expressions in target language
- Humor: Adapt while preserving comedic intent
- Poetry/Rhyme: Focus on meaning over literal translation

Think step by step:
1. Analyze source text structure and meaning
2. Identify specialized terminology
3. Consider target audience and purpose
4. Translate sentence by sentence
5. Review for flow and naturalness
6. Verify technical accuracy"""
    
    def get_examples(self) -> List[Dict[str, str]]:
        return [
            {
                "user": "Translate to Russian: 'The quick brown fox jumps over the lazy dog. This sentence contains all letters of the alphabet.'",
                "assistant": "Быстрая коричневая лиса прыгает через ленивую собаку. Это предложение содержит все буквы алфавита."
            }
        ]
    
    def _enhance_user_input(self, user_input: str, **kwargs) -> str:
        source_lang = kwargs.get("source_lang", "auto")
        target_lang = kwargs.get("target_lang", "Russian")
        preserve_formatting = kwargs.get("preserve_formatting", True)
        
        enhanced = f"""TRANSLATION REQUEST:
Source language: {source_lang}
Target language: {target_lang}
Preserve formatting: {preserve_formatting}

Text to translate:
{user_input}

Please provide accurate, natural-sounding translation."""
        
        return enhanced


class CodeGenerationPrompt(PromptTemplate):
    """Prompt template for code generation"""
    
    def __init__(self, version: PromptVersion = PromptVersion.V1):
        super().__init__(TaskType.CODE_GENERATION, version)
    
    def get_system_prompt(self) -> str:
        return """You are an expert software engineer with deep knowledge of multiple programming languages and best practices.
Generate clean, efficient, well-documented code that follows industry standards.

CODING STANDARDS:
1. Clean Code: Meaningful variable names, single responsibility functions
2. Error Handling: Comprehensive try-catch blocks, meaningful error messages
3. Documentation: Inline comments for complex logic, docstrings for functions
4. Testing: Include example usage or test cases
5. Security: Sanitize inputs, avoid common vulnerabilities
6. Performance: Optimize algorithms, consider time/space complexity
7. Maintainability: Modular design, separation of concerns

REQUIREMENTS:
- Use latest language features when appropriate
- Follow language-specific style guides (PEP 8 for Python, etc.)
- Include type hints/annotations
- Consider edge cases and boundary conditions
- Add TODO comments for potential improvements

Think step by step:
1. Understand the problem requirements
2. Design algorithm/architecture
3. Write pseudocode if complex
4. Implement with best practices
5. Add comments and documentation
6. Test with example cases"""
    
    def get_examples(self) -> List[Dict[str, str]]:
        return [
            {
                "user": "Write a Python function to validate email addresses with regex",
                "assistant": """import re
from typing import Optional

def validate_email(email: str) -> tuple[bool, Optional[str]]:
    \"\"\"
    Validate email address format using regex.
    
    Args:
        email: Email address string to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
        - is_valid: True if email format is valid
        - error_message: None if valid, error description if invalid
        
    Examples:
        >>> validate_email("user@example.com")
        (True, None)
        
        >>> validate_email("invalid-email")
        (False, "Invalid email format")
    \"\"\"
    # Comprehensive email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    
    if not email:
        return False, "Email cannot be empty"
    
    if len(email) > 254:  # RFC 5321 limit
        return False, "Email too long (max 254 characters)"
    
    # Check format with regex
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    # Additional checks
    if '..' in email:
        return False, "Invalid consecutive dots"
    
    if email.startswith('.') or email.endswith('.'):
        return False, "Email cannot start or end with dot"
    
    # Split local and domain parts
    local_part, domain = email.split('@', 1)
    
    if len(local_part) > 64:  # RFC 5321 limit
        return False, "Local part too long (max 64 characters)"
    
    return True, None


# Example usage and tests
if __name__ == "__main__":
    test_emails = [
        "user@example.com",
        "invalid-email",
        "user@.com",
        "a" * 65 + "@example.com",
        "user@example." + "a" * 250,
    ]
    
    for email in test_emails:
        is_valid, message = validate_email(email)
        print(f"{email}: {'✓' if is_valid else '✗'} {message or ''}")"""
            }
        ]
    
    def _enhance_user_input(self, user_input: str, **kwargs) -> str:
        language = kwargs.get("language", "Python")
        include_tests = kwargs.get("include_tests", True)
        add_comments = kwargs.get("add_comments", True)
        
        enhanced = f"""CODE GENERATION REQUEST:
Language: {language}
Include tests: {include_tests}
Add comments: {add_comments}

Requirements:
{user_input}

Please generate clean, well-documented code following best practices."""
        
        return enhanced


def get_prompt_template(task_type: TaskType, version: PromptVersion = PromptVersion.V1) -> PromptTemplate:
    """Factory function to get prompt template by task type"""
    templates = {
        TaskType.SEO_ARTICLE: SEOArticlePrompt,
        TaskType.TRANSLATION: TranslationPrompt,
        TaskType.CODE_GENERATION: CodeGenerationPrompt,
        # Add more template classes as needed
    }
    
    template_class = templates.get(task_type)
    if not template_class:
        raise ValueError(f"No template found for task type: {task_type}")
    
    return template_class(version)


def estimate_tokens(text: str) -> int:
    """Estimate token count for text (approximate: 1 token ≈ 4 characters)"""
    return len(text) // 4


class PromptMetrics:
    """Track prompt metrics for optimization"""
    
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "total_tokens_used": 0,
            "average_response_time": 0.0,
            "task_type_distribution": {},
            "version_performance": {},
        }
    
    def record_request(self, task_type: TaskType, version: PromptVersion, tokens_used: int, success: bool, response_time: float):
        """Record metrics for a prompt request"""
        self.metrics["total_requests"] += 1
        
        if success:
            self.metrics["successful_responses"] += 1
        else:
            self.metrics["failed_responses"] += 1
        
        self.metrics["total_tokens_used"] += tokens_used
        
        # Update average response time
        current_avg = self.metrics["average_response_time"]
        total_requests = self.metrics["total_requests"]
        self.metrics["average_response_time"] = (
            (current_avg * (total_requests - 1) + response_time) / total_requests
        )
        
        # Update task type distribution
        task_key = task_type.value
        self.metrics["task_type_distribution"][task_key] = self.metrics["task_type_distribution"].get(task_key, 0) + 1
        
        # Update version performance
        version_key = f"{task_type.value}_{version.value}"
        if version_key not in self.metrics["version_performance"]:
            self.metrics["version_performance"][version_key] = {
                "requests": 0,
                "successes": 0,
                "total_tokens": 0,
            }
        
        self.metrics["version_performance"][version_key]["requests"] += 1
        if success:
            self.metrics["version_performance"][version_key]["successes"] += 1
        self.metrics["version_performance"][version_key]["total_tokens"] += tokens_used
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics.copy()
    
    def get_success_rate(self) -> float:
        """Calculate overall success rate"""
        total = self.metrics["total_requests"]
        if total == 0:
            return 0.0
        return self.metrics["successful_responses"] / total * 100
    
    def get_average_tokens_per_request(self) -> float:
        """Calculate average tokens per request"""
        total = self.metrics["total_requests"]
        if total == 0:
            return 0.0
        return self.metrics["total_tokens_used"] / total


# Global metrics instance
prompt_metrics = PromptMetrics()
