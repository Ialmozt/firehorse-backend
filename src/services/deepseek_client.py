"""
DeepSeek API client for content generation.
"""
import logging
import httpx
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """Client for DeepSeek API"""
    
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.timeout = 60.0
        
        if not self.api_key:
            logger.warning("⚠️ DEEPSEEK_API_KEY not set in environment")
    
    async def generate_content(self, prompt: str, topic: str = "general", max_tokens: int = 2000) -> Dict[str, Any]:
        """
        Generate content using DeepSeek API.
        
        Args:
            prompt: The prompt for content generation
            topic: Topic/category for better prompt engineering
            max_tokens: Maximum tokens in response
            
        Returns:
            Dict with generated content and metadata
        """
        if not self.api_key:
            logger.error("❌ Cannot generate content: DEEPSEEK_API_KEY not set")
            return {
                "success": False,
                "error": "DEEPSEEK_API_KEY not configured",
                "content": None
            }
        
        try:
            # Enhanced prompt based on topic
            enhanced_prompt = self._enhance_prompt(prompt, topic)
            
            # Prepare request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": self._get_system_prompt(topic)
                    },
                    {
                        "role": "user",
                        "content": enhanced_prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "stream": False
            }
            
            logger.info(f"🤖 Calling DeepSeek API for topic: {topic}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    logger.info(f"✅ DeepSeek content generated: {len(content)} characters")
                    
                    return {
                        "success": True,
                        "content": content,
                        "model": data.get("model", "deepseek-chat"),
                        "usage": data.get("usage", {}),
                        "topic": topic
                    }
                else:
                    error_msg = f"DeepSeek API error: {response.status_code} - {response.text}"
                    logger.error(f"❌ {error_msg}")
                    
                    return {
                        "success": False,
                        "error": error_msg,
                        "content": None
                    }
                    
        except httpx.TimeoutException:
            error_msg = "DeepSeek API timeout"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "content": None
            }
            
        except Exception as e:
            error_msg = f"DeepSeek API exception: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "content": None
            }
    
    def _enhance_prompt(self, prompt: str, topic: str) -> str:
        """Enhance user prompt based on topic"""
        topic_enhancements = {
            "seo": "Write SEO-optimized content with keywords, meta description, and headings. "
                   "Focus on search engine visibility and user engagement.",
            "article": "Write a well-structured article with introduction, body, and conclusion. "
                      "Use clear paragraphs and engaging language.",
            "translation": "Provide accurate translation while maintaining original meaning and tone. "
                          "Consider cultural nuances.",
            "copywriting": "Write persuasive copy that converts. Focus on benefits, clear CTAs, "
                          "and emotional appeal.",
            "social": "Create engaging social media content. Use appropriate tone for the platform, "
                     "include hashtags and emojis where suitable.",
            "programming": "Provide clear, well-commented code with explanations. "
                          "Include best practices and error handling.",
            "general": "Provide comprehensive, well-written content that addresses the user's request."
        }
        
        enhancement = topic_enhancements.get(topic, topic_enhancements["general"])
        return f"{enhancement}\n\nUser request: {prompt}"
    
    def _get_system_prompt(self, topic: str) -> str:
        """Get system prompt based on topic"""
        system_prompts = {
            "seo": "You are an expert SEO content writer. Create high-quality, "
                   "SEO-optimized content that ranks well in search engines.",
            "article": "You are a professional article writer. Create informative, "
                      "well-structured articles that engage readers.",
            "translation": "You are a professional translator. Provide accurate, "
                          "natural-sounding translations.",
            "copywriting": "You are a skilled copywriter. Create persuasive, "
                          "conversion-focused copy.",
            "social": "You are a social media expert. Create engaging, "
                     "platform-appropriate content.",
            "programming": "You are an expert programmer. Provide clean, "
                          "efficient code with clear explanations.",
            "general": "You are a helpful AI assistant. Provide high-quality, "
                      "detailed responses to user requests."
        }
        
        return system_prompts.get(topic, system_prompts["general"])
    
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


# Convenience function
async def generate_content_with_deepseek(prompt: str, topic: str = "general") -> Dict[str, Any]:
    """Convenience function for generating content"""
    client = DeepSeekClient()
    return await client.generate_content(prompt, topic)
