import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# --- PATH FIX ---
# Get the path to the project root (one level up from 'scripts')
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from sqlmodel import Session, select
from app.utils.db import engine
from app.models import Customer
from app.agent import agent, SupportDeps


if __name__ == "__main__":
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Warning: GOOGLE_API_KEY not found in .env file!")
        
    # Run the main function
    from app.models import Customer # Re-import inside main guard just to be safe
    
    print("--- 🛒 ShopSmart CLI Debugger ---")
    with Session(engine) as session:
        # Pick the first customer just to impersonate
        customer = session.exec(select(Customer)).first()

        if not customer:
            print("❌ Error: No customers found. Run the seed notebook first.")
            sys.exit(1)
            
        print(f"👤 Logged in as: {customer.name} (ID: {customer.id})")
        print("---------------------------------")
        
        while True:
            user_input = input("You: ")
            if user_input.lower() in ["quit", "exit"]:
                break
            
            deps = SupportDeps(user_id=customer.id, db=session)
            try:
                # Synchronous run for CLI testing
                result = agent.run_sync(user_input, deps=deps)
                print(f"🤖 Agent: {result.output}\n")
            except Exception as e:
                print(f"❌ Error: {e}")