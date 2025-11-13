#!/usr/bin/env python3
"""
Quick setup checker for Curiosity Agent
"""

import os
import sys

def check_file(filename, description):
    """Check if a file exists"""
    exists = os.path.exists(filename)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filename}")
    return exists

def check_env_var(var_name):
    """Check if environment variable is set"""
    exists = os.environ.get(var_name) is not None
    status = "✅" if exists else "❌"
    print(f"{status} Environment variable: {var_name}")
    return exists

def main():
    print("🔍 Checking Curiosity Agent Setup...\n")
    
    all_good = True
    
    # Check files
    print("Files:")
    all_good &= check_file("schema.json", "BigQuery schema")
    all_good &= check_file("training_data.csv", "Training data CSV")
    
    print("\nEnvironment Variables:")
    all_good &= check_env_var("OPENAI_API_KEY")
    
    print("\nScripts:")
    check_file("main.py", "Main monitoring agent")
    check_file("extract_schema.py", "Schema extractor")
    
    print("\n" + "="*60)
    
    if all_good:
        print("✅ All set! Ready to run:")
        print("   python main.py")
    else:
        print("❌ Setup incomplete. Follow these steps:\n")
        
        if not os.path.exists("schema.json"):
            print("1. Extract schema:")
            print("   python extract_schema.py\n")
        
        if not os.environ.get("OPENAI_API_KEY"):
            print("2. Set OpenAI API key:")
            print("   export OPENAI_API_KEY='your-key-here'\n")
        
        if not os.path.exists("training_data.csv"):
            print("3. Add training data CSV to this directory\n")
    
    print("="*60)

if __name__ == "__main__":
    main()
