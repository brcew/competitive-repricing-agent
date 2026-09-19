"""
Standalone script to run the integration test without starting the full system.

Usage: python run_integration_test.py
"""

import sys
from pathlib import Path

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

from test_integration import main
import asyncio

if __name__ == "__main__":
    print("Running OpenAI Client + Groq Integration Test...")
    print("This validates that our system can communicate with Groq models.\n")
    
    success = asyncio.run(main())
    
    if success:
        print("\n[SUCCESS] Integration test completed successfully!")
        print("The system is ready for agent development.")
        sys.exit(0)
    else:
        print("\n[FAILED] Integration test failed!")
        print("Please check your GROQ_API_KEY and network connectivity.")
        sys.exit(1)