"""
Advanced DeepSeek API client with prompt engineering features.
Features:
- Multi-shot prompting (few-shot examples)
- Chain-of-Thought (CoT) reasoning
- Role-based prompting
- Temperature optimization per task type
- Token budgeting and usage tracking
- Prompt caching for repeated queries
- A/B testing of prompt versions
"""

import logging
import httpx
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.config import settings
from src.prompts import (
    TaskType, PromptVersion, get_prompt_template,
    estimate_tokens, prompt_metrics
)

logger = logging.getLogger(__name__)


class PromptCache:
    """Cache for prompt templates to reduce token usage"""
    
    def __init__(self, max_size: int = 100, ttl_hours: int = 24):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
    
    def get_key(self, task_type: TaskType, version: PromptVersion, **kwargs) -> str:
        """Generate cache key from parameters"""
        key_parts = [task_type.value, version.value]
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool)):
                key_parts.append(f"{k}:{v}")
        return "|".join(key_parts)
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached prompt"""
        if key not in self.cache:
            return None
        
        cached_item = self.cache[key]
        if datetime.now() - cached_item["timestamp"] > self.ttl:
            del self.cache[key]
            return None
        
        return cached_item["prompt"]
    
    def set(self, key: str, prompt: Dict[str, Any]):
        """Cache prompt"""
        if len(self.cache) >= self.max_size:
            # Remove oldest item
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]
        
        self.cache[key] = {
            "prompt": prompt,
            "timestamp": datetime.now(),
            "hits": 0
        }
    
    def increment_hits(self, key: str):
        """Increment cache hit counter"""
        if key in self.cache:
            self.cache[key]["hits"] = self.cache[key].get("hits", 0) + 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_items = len(self.cache)
        total_hits = sum(item.get("hits", 0) for item in self.cache.values())
        
        return {
            "total_items": total_items,
            "total_hits": total_hits,
            "hit_rate": total_hits / (total_hits + total_items) if total_hits + total_items > 0 else 0,
            "oldest_item": min((item["timestamp"] for item in self.cache.values()), default=None),
            "most_hits": max((item.get("hits", 0) for item in self.cache.values()), default=0),
        }


class AdvancedDeepSeekClient:
    """Advanced DeepSeek API client with prompt engineering"""
    
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.timeout = 60.0
        self.prompt_cache = PromptCache()
        
        if not self.api_key:
            logger.warning("⚠️ DEEPSEEK_API_KEY not set in environment")
    
    async def generate_content(
        self,
        prompt: str,
        task_type: TaskType = TaskType.CONTENT_CREATION,
        version: PromptVersion = PromptVersion.V1,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate content using advanced prompt engineering.
        
        Args:
            prompt: User prompt for content generation
            task_type: Type of task (SEO, translation, code, etc.)
            version: Prompt version for A/B testing
            **kwargs: Additional parameters for prompt template
            
        Returns:
            Dict with generated content and metadata
        """
        if not self.api_key:
            logger.error("❌ Cannot generate content: DEEPSEEK_API_KEY not set")
            return self._error_response("DEEPSEEK_API_KEY not configured")
        
        start_time = time.time()
        cache_key = None
        
        try:
            # Try to get from cache
            cache_key = self.prompt_cache.get_key(task_type, version, **kwargs)
            cached_prompt = self.prompt_cache.get(cache_key)
            
            if cached_prompt:
                logger.info(f"📦 Using cached prompt for {task_type.value} (v{version.value})")
                self.prompt_cache.increment_hits(cache_key)
                messages = cached_prompt["messages"]
                temperature = cached_prompt["temperature"]
                max_tokens = cached_prompt["max_tokens"]
            else:
                # Build prompt using template
                prompt_template = get_prompt_template(task_type, version)
                prompt_data = prompt_template.build_prompt(prompt, **kwargs)
                
                messages = prompt_data["messages"]
                temperature = prompt_data["temperature"]
                max_tokens = prompt_data["max_tokens"]
                
                # Cache the prompt
                if cache_key:
                    self.prompt_cache.set(cache_key, {
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "task_type": task_type.value,
                        "version": version.value,
                    })
            
            # Prepare request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            
            logger.info(f"🤖 Calling DeepSeek API for {task_type.value} (v{version.value})")
            logger.debug(f"Prompt temperature: {temperature}, max tokens: {max_tokens}")
            
            # Make API call
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    tokens_used = usage.get("total_tokens", 0)
                    
                    # Record metrics
                    prompt_metrics.record_request(
                        task_type=task_type,
                        version=version,
                        tokens_used=tokens_used,
                        success=True,
                        response_time=response_time
                    )
                    
                    logger.info(
                        f"✅ DeepSeek content generated: {len(content)} characters, "
                        f"{tokens_used} tokens, {response_time:.2f}s"
                    )
                    
                    return {
                        "success": True,
                        "content": content,
                        "model": data.get("model", "deepseek-chat"),
                        "usage": usage,
                        "task_type": task_type.value,
                        "version": version.value,
                        "response_time": response_time,
                        "cache_hit": cached_prompt is not None,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                else:
                    error_msg = f"DeepSeek API error: {response.status_code} - {response.text}"
                    logger.error(f"❌ {error_msg}")
                    
                    # Record failure metrics
                    prompt_metrics.record_request(
                        task_type=task_type,
                        version=version,
                        tokens_used=0,
                        success=False,
                        response_time=response_time
                    )
                    
                    return self._error_response(error_msg)
                    
        except httpx.TimeoutException:
            response_time = time.time() - start_time
            error_msg = "DeepSeek API timeout"
            logger.error(f"❌ {error_msg}")
            
            prompt_metrics.record_request(
                task_type=task_type,
                version=version,
                tokens_used=0,
                success=False,
                response_time=response_time
            )
            
            return self._error_response(error_msg)
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"DeepSeek API exception: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            prompt_metrics.record_request(
                task_type=task_type,
                version=version,
                tokens_used=0,
                success=False,
                response_time=response_time
            )
            
            return self._error_response(error_msg)
    
    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "success": False,
            "error": error_msg,
            "content": None,
            "task_type": None,
            "version": None,
            "response_time": 0.0,
            "cache_hit": False,
        }
    
    async def generate_with_retry(
        self,
        prompt: str,
        task_type: TaskType = TaskType.CONTENT_CREATION,
        version: PromptVersion = PromptVersion.V1,
        max_retries: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate content with retry logic and exponential backoff.
        
        Args:
            prompt: User prompt
            task_type: Type of task
            version: Prompt version
            max_retries: Maximum number of retries
            **kwargs: Additional parameters
            
        Returns:
            Dict with generated content or error
        """
        for attempt in range(max_retries):
            try:
                result = await self.generate_content(prompt, task_type, version, **kwargs)
                
                if result["success"]:
                    return result
                
                # If failed, wait and retry
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"⚠️ Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    
                    # Try different version on retry
                    if version == PromptVersion.V1:
                        version = PromptVersion.V2
                    elif version == PromptVersion.V2:
                        version = PromptVersion.V3
                    else:
                        version = PromptVersion.V1
                    
            except Exception as e:
                logger.error(f"❌ Attempt {attempt + 1} failed with exception: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
        
        # All retries failed
        return self._error_response(f"All {max_retries} attempts failed")
    
    async def batch_generate(
        self,
        prompts: List[str],
        task_type: TaskType = TaskType.CONTENT_CREATION,
        version: PromptVersion = PromptVersion.V1,
        max_concurrent: int = 3,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generate content for multiple prompts concurrently.
        
        Args:
            prompts: List of user prompts
            task_type: Type of task
            version: Prompt version
            max_concurrent: Maximum concurrent requests
            **kwargs: Additional parameters
            
        Returns:
            List of results for each prompt
        """
        import asyncio
        from typing import List as TypingList
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_with_semaphore(prompt: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.generate_content(prompt, task_type, version, **kwargs)
        
        # Create tasks
        tasks = [generate_with_semaphore(prompt) for prompt in prompts]
        
        # Run concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results: TypingList[Dict[str, Any]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Error processing prompt {i}: {result}")
                processed_results.append(self._error_response(str(result)))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def test_connection(self) -> bool:
        """Test DeepSeek API connection"""
        if not self.api_key:
            logger.warning("⚠️ Cannot test connection: DEEPSEEK_API_KEY not set")
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "Say 'Hello'"}],
                "max_tokens": 10
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"❌ DeepSeek connection test failed: {str(e)}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get prompt cache statistics"""
        return self.prompt_cache.get_stats()
    
    def get_prompt_metrics(self) -> Dict[str, Any]:
        """Get prompt engineering metrics"""
        metrics = prompt_metrics.get_metrics()
        metrics["success_rate"] = prompt_metrics.get_success_rate()
        metrics["avg_tokens_per_request"] = prompt_metrics.get_average_tokens_per_request()
        return metrics


# Convenience functions
async def generate_seo_article(
    topic: str,
    keywords: str = "",
    word_count: int = 1500,
    tone: str = "professional",
    version: PromptVersion = PromptVersion.V1
) -> Dict[str, Any]:
    """Generate SEO article with advanced prompting"""
    client = AdvancedDeepSeekClient()
    return await client.generate_content(
        prompt=topic,
        task_type=TaskType.SEO_ARTICLE,
        version=version,
        keywords=keywords,
        word_count=word_count,
        tone=tone
    )


async def generate_translation(
    text: str,
    target_lang: str = "Russian",
    source_lang: str = "auto",
    preserve_formatting: bool = True,
    version: PromptVersion = PromptVersion.V1
) -> Dict[str, Any]:
    """Generate translation with advanced prompting"""
    client = AdvancedDeepSeekClient()
    return await client.generate_content(
        prompt=text,
        task_type=TaskType.TRANSLATION,
        version=version,
        target_lang=target_lang,
        source_lang=source_lang,
        preserve_formatting=preserve_formatting
    )


async def generate_code(
    requirements: str,
    language: str = "Python",
    include_tests: bool = True,
    add_comments: bool = True,
    version: PromptVersion = PromptVersion.V1
) -> Dict[str, Any]:
    """Generate code with advanced prompting"""
    client = AdvancedDeepSeekClient()
    return await client.generate_content(
        prompt=requirements,
        task_type=TaskType.CODE_GENERATION,
        version=version,
        language=language,
        include_tests=include_tests,
        add_comments=add_comments
    )


# Import asyncio for convenience functions
import asyncio
