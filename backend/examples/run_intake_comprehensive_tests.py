"""
Example script to run comprehensive Intake Agent tests

This script demonstrates how to run the comprehensive test suite for Task 8.8.

Usage:
    python backend/examples/run_intake_comprehensive_tests.py
"""

import subprocess
import sys
import os


def run_tests():
    """Run comprehensive Intake Agent tests."""
    print("=" * 80)
    print("Running Comprehensive Intake Agent Tests (Task 8.8)")
    print("=" * 80)
    print()
    
    # Set environment variables for testing
    os.environ.setdefault("GEMINI_API_KEY", "test-key")
    os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
    
    # Test categories
    test_categories = [
        ("Unit Tests (8.8.1)", "test_intake_comprehensive.py::TestCrewAIAgentInitialization"),
        ("Unit Tests (8.8.1)", "test_intake_comprehensive.py::TestLeadCaptureFromMultipleSources"),
        ("Unit Tests (8.8.1)", "test_intake_comprehensive.py::TestUrgencyClassification"),
        ("Unit Tests (8.8.1)", "test_intake_comprehensive.py::TestServiceTypeDetection"),
        ("Unit Tests (8.8.1)", "test_intake_comprehensive.py::TestConfidenceScoring"),
        ("Unit Tests (8.8.1)", "test_intake_comprehensive.py::TestPartsAvailabilityChecking"),
        ("Unit Tests (8.8.1)", "test_intake_comprehensive.py::TestNotificationCreation"),
        ("Integration Tests (8.8.2)", "test_intake_comprehensive.py::TestCompleteIntakeFlow"),
        ("Integration Tests (8.8.2)", "test_intake_comprehensive.py::TestWebRTCVoiceIntegration"),
        ("Integration Tests (8.8.2)", "test_intake_comprehensive.py::TestInventoryServiceIntegration"),
        ("Integration Tests (8.8.2)", "test_intake_comprehensive.py::TestNotificationDeliveryAllChannels"),
        ("Integration Tests (8.8.2)", "test_intake_comprehensive.py::TestLLMIntegrationForClassification"),
        ("System Tests (8.8.3)", "test_intake_comprehensive.py::TestIntakePerformanceUnderLoad"),
        ("System Tests (8.8.3)", "test_intake_comprehensive.py::TestClassificationAccuracyWithRealData"),
        ("System Tests (8.8.3)", "test_intake_comprehensive.py::TestNotificationDeliveryReliability"),
        ("System Tests (8.8.3)", "test_intake_comprehensive.py::TestWebRTCSessionManagement"),
        ("System Tests (8.8.3)", "test_intake_comprehensive.py::TestRequirementsValidation"),
        ("End-to-End Tests (8.8.4)", "test_intake_comprehensive.py::TestCompleteCustomerIntake"),
        ("End-to-End Tests (8.8.4)", "test_intake_comprehensive.py::TestMultiChannelIntake"),
        ("End-to-End Tests (8.8.4)", "test_intake_comprehensive.py::TestErrorHandlingAndFallback"),
        ("Statistics Tests", "test_intake_comprehensive.py::TestAgentStatistics"),
    ]
    
    print("Test Categories:")
    for category, _ in test_categories:
        if category not in [c for c, _ in test_categories[:test_categories.index((category, _))]]:
            print(f"  - {category}")
    print()
    
    # Run all tests
    print("Running all comprehensive tests...")
    print()
    
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "backend/tests/test_intake_comprehensive.py",
        "-v",
        "-s",
        "--tb=short",
        "--color=yes",
    ]
    
    result = subprocess.run(cmd, cwd=os.getcwd())
    
    print()
    print("=" * 80)
    if result.returncode == 0:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed. See output above for details.")
    print("=" * 80)
    
    return result.returncode


def run_specific_category(category_name):
    """Run tests for a specific category."""
    print(f"Running {category_name} tests...")
    print()
    
    category_map = {
        "unit": "test_intake_comprehensive.py -k 'Test' -k 'not Integration' -k 'not System' -k 'not E2E'",
        "integration": "test_intake_comprehensive.py::TestCompleteIntakeFlow or test_intake_comprehensive.py::TestWebRTCVoiceIntegration",
        "system": "test_intake_comprehensive.py -k 'Performance or Accuracy or Reliability or Session or Requirements'",
        "e2e": "test_intake_comprehensive.py -m e2e",
    }
    
    if category_name not in category_map:
        print(f"Unknown category: {category_name}")
        print(f"Available categories: {', '.join(category_map.keys())}")
        return 1
    
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "backend/tests/" + category_map[category_name],
        "-v",
        "-s",
        "--tb=short",
    ]
    
    result = subprocess.run(cmd, cwd=os.getcwd())
    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) > 1:
        category = sys.argv[1].lower()
        exit_code = run_specific_category(category)
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)
