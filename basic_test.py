#!/usr/bin/env python3

print("=== Start Basic Test ===")

import sys
print(f"Python versie: {sys.version}")
print(f"Python pad: {sys.executable}")

print("\nTest environment variables:")
import os
from dotenv import load_dotenv

# Probeer .env te laden
load_dotenv()

# Print working directory
print(f"\nHuidige directory: {os.getcwd()}")
print("Bestanden in directory:")
for file in os.listdir():
    if file.endswith('.py') or file.endswith('.env'):
        print(f"- {file}")

print("\n=== Test Compleet ===") 