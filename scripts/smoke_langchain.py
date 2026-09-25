"""Quick test: verify LangChain agent imports and app creation."""
import sys
import traceback

try:
    print("Step 1: Importing app factory...")
    from backend.app import create_app
    print("  OK")
    
    print("Step 2: Creating Flask app...")
    app = create_app()
    print("  OK")
    
    print("Step 3: Testing agent imports...")
    with app.app_context():
        from backend.agents import get_orchestrator
        orchestrator = get_orchestrator()
        print(f"  OK - {len(orchestrator.agents)} agents registered")
        
        print("\nStep 4: Agent status:")
        for name, agent in orchestrator.agents.items():
            status = agent.get_status()
            tools = status.get('tools', [])
            llm = status.get('llm', 'N/A')
            print(f"  {name} v{status['version']} | LLM: {llm} | Tools: {tools}")
        
        print(f"\nStep 5: Pipeline info:")
        info = orchestrator.get_pipeline_info()
        print(f"  Framework: {info['framework']}")
        print(f"  LLM Provider: {info['llm_provider']}")
        print(f"  LLM Available: {info['llm_available']}")
    
    print("\n=== ALL TESTS PASSED ===")

except Exception as e:
    print(f"\nERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
