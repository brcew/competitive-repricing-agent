"""
Hello-world agent to validate OpenAI client + Groq integration.

This validation step confirms that we can communicate with Groq models
using the OpenAI-compatible API before building the real agents.
NOTE: We use direct OpenAI client instead of ADK + LiteLLM due to dependency complexity.
"""

import asyncio
import os
from typing import Any, Dict

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel

from config import settings

logger = structlog.get_logger(__name__)


class HelloWorldInput(BaseModel):
    """Input schema for the hello world agent."""
    message: str = "Hello from competitive pricing system!"


class HelloWorldAgent:
    """Simple agent to validate OpenAI client + Groq integration."""
    
    def __init__(self):
        """Initialize the hello world agent."""
        # Validate API key is present
        if not settings.groq_api_key or settings.groq_api_key == "your_groq_api_key_here":
            raise ValueError(
                "GROQ_API_KEY not set. Please set it in your .env file or environment."
            )
        
        # Initialize OpenAI client pointing to Groq
        self.client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        
        # Extract model names (remove groq/ prefix if present)
        self.orchestrator_model = settings.orchestrator_model.replace("groq/", "")
        self.worker_model = settings.worker_model.replace("groq/", "")
    
    async def test_orchestrator(self, input_data: HelloWorldInput) -> Dict[str, Any]:
        """Test the orchestrator agent (70b model)."""
        logger.info("Testing orchestrator agent", model=self.orchestrator_model)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.orchestrator_model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a test orchestrator agent for a competitive pricing system.
            
Your job is to respond with a brief confirmation that you can:
1. Understand the input message
2. Access your model capabilities
3. Respond in a structured way

Keep your response under 100 words and mention that you're the orchestrator tier."""
                    },
                    {
                        "role": "user",
                        "content": f"Test message: {input_data.message}\n\nPlease confirm you received this and are the orchestrator agent."
                    }
                ],
                max_tokens=150,
                temperature=0.1
            )
            
            return {
                "success": True,
                "model": self.orchestrator_model,
                "response": response.choices[0].message.content,
                "agent_type": "orchestrator",
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            logger.error("Orchestrator agent failed", error=str(e))
            return {
                "success": False,
                "model": self.orchestrator_model,
                "error": str(e),
                "agent_type": "orchestrator"
            }
    
    async def test_worker(self, input_data: HelloWorldInput) -> Dict[str, Any]:
        """Test the worker agent (8b model)."""
        logger.info("Testing worker agent", model=self.worker_model)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.worker_model,
                messages=[
                    {
                        "role": "system", 
                        "content": """You are a test worker agent for a competitive pricing system.
            
Your job is to respond with a brief confirmation that you can:
1. Understand the input message  
2. Access your model capabilities
3. Respond in a structured way

Keep your response under 50 words and mention that you're the worker tier."""
                    },
                    {
                        "role": "user",
                        "content": f"Test message: {input_data.message}\n\nPlease confirm you received this and are the worker agent."
                    }
                ],
                max_tokens=100,
                temperature=0.1
            )
            
            return {
                "success": True,
                "model": self.worker_model,
                "response": response.choices[0].message.content,
                "agent_type": "worker",
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            logger.error("Worker agent failed", error=str(e))
            return {
                "success": False,
                "model": self.worker_model,
                "error": str(e),
                "agent_type": "worker"
            }
    
    async def run_full_test(self) -> Dict[str, Any]:
        """Run complete integration test for both agents."""
        logger.info("Starting ADK + LiteLLM + Groq integration test")
        
        input_data = HelloWorldInput()
        
        # Test both agents concurrently
        orchestrator_result, worker_result = await asyncio.gather(
            self.test_orchestrator(input_data),
            self.test_worker(input_data),
            return_exceptions=True
        )
        
        # Handle any exceptions from gather
        if isinstance(orchestrator_result, Exception):
            orchestrator_result = {
                "success": False,
                "model": settings.orchestrator_model,
                "error": str(orchestrator_result),
                "agent_type": "orchestrator"
            }
        
        if isinstance(worker_result, Exception):
            worker_result = {
                "success": False,
                "model": settings.worker_model,
                "error": str(worker_result),
                "agent_type": "worker"
            }
        
        # Compile results
        results = {
            "integration_test_complete": True,
            "orchestrator": orchestrator_result,
            "worker": worker_result,
            "overall_success": orchestrator_result["success"] and worker_result["success"]
        }
        
        # Log summary
        if results["overall_success"]:
            logger.info("✅ Integration test PASSED", 
                       orchestrator_model=self.orchestrator_model,
                       worker_model=self.worker_model)
        else:
            logger.error("❌ Integration test FAILED",
                        orchestrator_success=orchestrator_result["success"],
                        worker_success=worker_result["success"])
        
        return results


async def main():
    """Run the hello world integration test."""
    try:
        agent = HelloWorldAgent()
        results = await agent.run_full_test()
        
        print("\n" + "="*60)
        print("OpenAI Client + Groq Integration Test Results")
        print("="*60)
        
        print(f"\nOrchestrator Agent ({agent.orchestrator_model}):")
        print(f"Status: {'✅ PASS' if results['orchestrator']['success'] else '❌ FAIL'}")
        if results['orchestrator']['success']:
            print(f"Response: {results['orchestrator']['response']}")
            print(f"Tokens used: {results['orchestrator'].get('tokens_used', 'unknown')}")
        else:
            print(f"Error: {results['orchestrator']['error']}")
        
        print(f"\nWorker Agent ({agent.worker_model}):")
        print(f"Status: {'✅ PASS' if results['worker']['success'] else '❌ FAIL'}")
        if results['worker']['success']:
            print(f"Response: {results['worker']['response']}")
            print(f"Tokens used: {results['worker'].get('tokens_used', 'unknown')}")
        else:
            print(f"Error: {results['worker']['error']}")
        
        print(f"\nOverall Integration: {'✅ PASS' if results['overall_success'] else '❌ FAIL'}")
        
        if results['overall_success']:
            print("\n🎉 Integration validated! Ready to build the real agents.")
            print("Note: Using OpenAI client directly for Groq compatibility.")
        else:
            print("\n⚠️  Integration failed. Check API key and network connectivity.")
            
        return results['overall_success']
        
    except Exception as e:
        logger.error("Integration test crashed", error=str(e))
        print(f"\n💥 Integration test crashed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())