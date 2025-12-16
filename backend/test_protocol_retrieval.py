#!/usr/bin/env python3
"""
Test script to verify protocol retrieval and EMS chatbot functionality.
"""

import sys
import io
from pathlib import Path
import json

# Set encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from main import retrieve_relevant_protocols, AVAILABLE_PROTOCOLS, detect_intent

def test_protocol_retrieval():
    """Test that protocols are loaded and retrieval works."""
    print(f"[OK] Loaded {len(AVAILABLE_PROTOCOLS)} protocols from RAG store")
    print(f"  Sample protocols: {list(AVAILABLE_PROTOCOLS.values())[:5]}")
    print()

def test_queries():
    """Test various EMS queries."""
    test_cases = [
        ("9 year old with allergic reaction", "allergic reaction - pediatric"),
        ("Patient with chest pain", "chest pain/cardiac"),
        ("3 month old not breathing", "respiratory/pediatric"),
        ("Adult with seizure", "seizure"),
        ("Child with severe burns", "burns/pediatric"),
        ("Drowning victim", "drowning"),
    ]
    
    print("Testing EMS Query Intent Detection & Protocol Retrieval:")
    print("=" * 70)
    
    for query, description in test_cases:
        intent = detect_intent(query)
        protocols = retrieve_relevant_protocols(query, top_k=3)
        
        print(f"\nQuery: {query}")
        print(f"Description: {description}")
        print(f"Intent: {intent}")
        print(f"Retrieved Protocols:")
        if protocols:
            for i, protocol in enumerate(protocols, 1):
                print(f"  {i}. {protocol}")
        else:
            print("  (none matched)")
        print("-" * 70)

if __name__ == "__main__":
    test_protocol_retrieval()
    test_queries()
