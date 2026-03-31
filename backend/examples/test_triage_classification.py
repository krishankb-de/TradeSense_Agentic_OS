"""
Test script for Task 8.2: Triage and Classification Logic

This script demonstrates the new urgency classification and service type detection
capabilities of the Intake Agent.

Validates: Requirements 4.3, 4.4
"""

import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.intake import IntakeAgent, LeadInput, LeadSource, CustomerInfo, UrgencyLevel
from llm.unified_client import UnifiedLLMClient
from db.models import Lead, Customer
from db.session import get_db


async def test_urgency_classification():
    """Test urgency classification with various scenarios."""
    print("\n" + "="*80)
    print("TEST 1: Urgency Classification")
    print("="*80)
    
    # Initialize LLM client (mock mode for testing)
    llm_client = UnifiedLLMClient(
        gemini_api_key="test-key",
        azure_api_key="test-key",
        azure_endpoint="https://test.openai.azure.com"
    )
    
    # Create intake agent
    agent = IntakeAgent(llm_client=llm_client)
    
    # Test cases
    test_cases = [
        {
            "description": "Gas leak in the basement, strong smell",
            "expected_urgency": "emergency",
        },
        {
            "description": "Furnace stopped working and it's freezing cold",
            "expected_urgency": "emergency",
        },
        {
            "description": "AC not working, house is getting hot",
            "expected_urgency": "urgent",
        },
        {
            "description": "Water heater making strange noises",
            "expected_urgency": "urgent",
        },
        {
            "description": "Need annual HVAC maintenance check",
            "expected_urgency": "routine",
        },
        {
            "description": "Want to schedule a tune-up for my furnace",
            "expected_urgency": "routine",
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Description: {test_case['description']}")
        print(f"Expected Urgency: {test_case['expected_urgency']}")
        
        try:
            result = await agent._classify_urgency(test_case['description'])
            print(f"Classified Urgency: {result['urgency']}")
            print(f"Confidence: {result['confidence']:.2%}")
            print(f"Reasoning: {result['reasoning'][:100]}...")
            
            # Check if classification matches expectation
            if result['urgency'] == test_case['expected_urgency']:
                print("✓ PASS: Classification matches expected urgency")
            else:
                print(f"✗ FAIL: Expected {test_case['expected_urgency']}, got {result['urgency']}")
        except Exception as e:
            print(f"✗ ERROR: {e}")


async def test_service_type_detection():
    """Test service type detection with various scenarios."""
    print("\n" + "="*80)
    print("TEST 2: Service Type Detection")
    print("="*80)
    
    # Initialize LLM client (mock mode for testing)
    llm_client = UnifiedLLMClient(
        gemini_api_key="test-key",
        azure_api_key="test-key",
        azure_endpoint="https://test.openai.azure.com"
    )
    
    # Create intake agent
    agent = IntakeAgent(llm_client=llm_client)
    
    # Test cases
    test_cases = [
        {
            "description": "My furnace stopped working",
            "expected_service": "HVAC",
        },
        {
            "description": "Thermostat not responding",
            "expected_service": "HVAC",
        },
        {
            "description": "Toilet is clogged and overflowing",
            "expected_service": "Plumbing",
        },
        {
            "description": "Water heater leaking",
            "expected_service": "Plumbing",
        },
        {
            "description": "No power in the kitchen outlets",
            "expected_service": "Electrical",
        },
        {
            "description": "Lights flickering throughout the house",
            "expected_service": "Electrical",
        },
        {
            "description": "Refrigerator not cooling",
            "expected_service": "Appliance",
        },
        {
            "description": "Dishwasher won't start",
            "expected_service": "Appliance",
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Description: {test_case['description']}")
        print(f"Expected Service: {test_case['expected_service']}")
        
        try:
            result = await agent._detect_service_type(test_case['description'])
            print(f"Detected Service: {result['service_type']}")
            print(f"Confidence: {result['confidence']:.2%}")
            print(f"Reasoning: {result['reasoning'][:100]}...")
            
            # Check if detection matches expectation
            if result['service_type'] == test_case['expected_service']:
                print("✓ PASS: Detection matches expected service type")
            else:
                print(f"✗ FAIL: Expected {test_case['expected_service']}, got {result['service_type']}")
        except Exception as e:
            print(f"✗ ERROR: {e}")


async def test_confidence_scoring():
    """Test confidence score calculation."""
    print("\n" + "="*80)
    print("TEST 3: Confidence Scoring")
    print("="*80)
    
    # Initialize LLM client (mock mode for testing)
    llm_client = UnifiedLLMClient(
        gemini_api_key="test-key",
        azure_api_key="test-key",
        azure_endpoint="https://test.openai.azure.com"
    )
    
    # Create intake agent
    agent = IntakeAgent(llm_client=llm_client)
    
    # Test cases with different confidence levels
    test_cases = [
        {
            "urgency_result": {"urgency": "emergency", "confidence": 0.95, "reasoning": "Gas leak"},
            "service_result": {"service_type": "HVAC", "confidence": 0.90, "reasoning": "Furnace issue"},
            "expected_range": (0.85, 1.0),
        },
        {
            "urgency_result": {"urgency": "urgent", "confidence": 0.80, "reasoning": "Not working"},
            "service_result": {"service_type": "Plumbing", "confidence": 0.75, "reasoning": "Water issue"},
            "expected_range": (0.70, 0.85),
        },
        {
            "urgency_result": {"urgency": "routine", "confidence": 0.70, "reasoning": "Maintenance"},
            "service_result": {"service_type": "General", "confidence": 0.65, "reasoning": "General repair"},
            "expected_range": (0.60, 0.75),
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Urgency Confidence: {test_case['urgency_result']['confidence']:.2%}")
        print(f"Service Confidence: {test_case['service_result']['confidence']:.2%}")
        
        confidence = agent._calculate_confidence(
            test_case['urgency_result'],
            test_case['service_result']
        )
        
        print(f"Overall Confidence: {confidence:.2%}")
        
        # Check if confidence is in expected range
        min_conf, max_conf = test_case['expected_range']
        if min_conf <= confidence <= max_conf:
            print(f"✓ PASS: Confidence in expected range ({min_conf:.0%}-{max_conf:.0%})")
        else:
            print(f"✗ FAIL: Confidence {confidence:.2%} outside expected range ({min_conf:.0%}-{max_conf:.0%})")


async def test_duration_estimation():
    """Test duration estimation logic."""
    print("\n" + "="*80)
    print("TEST 4: Duration Estimation")
    print("="*80)
    
    # Initialize LLM client (mock mode for testing)
    llm_client = UnifiedLLMClient(
        gemini_api_key="test-key",
        azure_api_key="test-key",
        azure_endpoint="https://test.openai.azure.com"
    )
    
    # Create intake agent
    agent = IntakeAgent(llm_client=llm_client)
    
    # Test cases
    test_cases = [
        {"service": "HVAC", "urgency": "emergency", "expected_min": 150, "expected_max": 200},
        {"service": "HVAC", "urgency": "urgent", "expected_min": 100, "expected_max": 140},
        {"service": "HVAC", "urgency": "routine", "expected_min": 80, "expected_max": 110},
        {"service": "Plumbing", "urgency": "emergency", "expected_min": 120, "expected_max": 150},
        {"service": "Electrical", "urgency": "urgent", "expected_min": 50, "expected_max": 70},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Service: {test_case['service']}, Urgency: {test_case['urgency']}")
        
        duration = agent._estimate_duration(test_case['service'], test_case['urgency'])
        print(f"Estimated Duration: {duration} minutes")
        
        # Check if duration is in expected range
        if test_case['expected_min'] <= duration <= test_case['expected_max']:
            print(f"✓ PASS: Duration in expected range ({test_case['expected_min']}-{test_case['expected_max']} min)")
        else:
            print(f"✗ FAIL: Duration {duration} outside expected range")


async def test_priority_calculation():
    """Test priority score calculation."""
    print("\n" + "="*80)
    print("TEST 5: Priority Calculation")
    print("="*80)
    
    # Initialize LLM client (mock mode for testing)
    llm_client = UnifiedLLMClient(
        gemini_api_key="test-key",
        azure_api_key="test-key",
        azure_endpoint="https://test.openai.azure.com"
    )
    
    # Create intake agent
    agent = IntakeAgent(llm_client=llm_client)
    
    # Test cases
    test_cases = [
        {"urgency": "emergency", "confidence": 0.95, "expected_priority": 10},
        {"urgency": "emergency", "confidence": 0.65, "expected_priority": 9},
        {"urgency": "urgent", "confidence": 0.85, "expected_priority": 6},
        {"urgency": "urgent", "confidence": 0.60, "expected_priority": 5},
        {"urgency": "routine", "confidence": 0.80, "expected_priority": 3},
        {"urgency": "routine", "confidence": 0.65, "expected_priority": 2},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Urgency: {test_case['urgency']}, Confidence: {test_case['confidence']:.2%}")
        
        priority = agent._calculate_priority(test_case['urgency'], test_case['confidence'])
        print(f"Priority Score: {priority}/10")
        
        # Check if priority matches expected
        if priority == test_case['expected_priority']:
            print(f"✓ PASS: Priority matches expected value")
        else:
            print(f"✗ FAIL: Expected {test_case['expected_priority']}, got {priority}")


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("TASK 8.2: TRIAGE AND CLASSIFICATION LOGIC TESTS")
    print("Validates: Requirements 4.3, 4.4")
    print("="*80)
    
    try:
        await test_urgency_classification()
        await test_service_type_detection()
        await test_confidence_scoring()
        await test_duration_estimation()
        await test_priority_calculation()
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
