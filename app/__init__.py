# Load environment variables FIRST, before any other imports
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
loaded = load_dotenv(env_path, override=True)

if loaded and os.path.exists(env_path):
    print("=" * 80)
    print(f"✅ ENVIRONMENT VARIABLES LOADED FROM: {env_path}")
    print("=" * 80)

    # Read .env file and print all variables dynamically
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Extract variable name (before '=')
            if '=' in line:
                var_name = line.split('=')[0].strip()
                var_value = os.getenv(var_name)
                # Truncate long values for readability
                if var_value and len(var_value) > 80:
                    var_value = var_value[:77] + "..."
                print(f"  {var_name}: {var_value}")

    print("=" * 80)

from app.agent import root_agent

__all__ = ["root_agent"]
