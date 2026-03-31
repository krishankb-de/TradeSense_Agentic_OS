"""
Example: Intake Agent Inventory Integration

Demonstrates the inventory checking and parts search functionality
integrated into the Intake Agent.

Usage:
    python -m backend.examples.test_intake_inventory
"""

import asyncio
import logging
from uuid import uuid4
from datetime import datetime

from agents.intake import (
    IntakeAgent,
    PartQuery,
    LeadInput,
    CustomerInfo,
    LeadSource,
)
from llm.unified_client import UnifiedLLMClient
from db.models import Part, Lead, Customer
from db.session import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def setup_sample_parts():
    """Create sample parts in database for testing."""
    logger.info("Setting up sample parts in database...")
    
    db = next(get_db())
    
    try:
        # Check if parts already exist
        existing = db.query(Part).filter(Part.part_number == "HVAC-THERM-001").first()
        if existing:
            logger.info("Sample parts already exist, skipping setup")
            return
        
        # Create sample parts
        parts = [
            Part(
                id=uuid4(),
                part_number="HVAC-THERM-001",
                name="Digital Thermostat",
                description="Programmable digital thermostat with WiFi",
                manufacturer="Honeywell",
                category="HVAC",
                quantity_available=15,
                unit_price=125.00,
                reorder_level=5,
            ),
            Part(
                id=uuid4(),
                part_number="HVAC-CAP-002",
                name="Run Capacitor 45/5",
                description="Dual run capacitor 45/5 MFD 370V",
                manufacturer="GE",
                category="HVAC",
                quantity_available=3,
                unit_price=35.00,
                reorder_level=10,
            ),
            Part(
                id=uuid4(),
                part_number="HVAC-CAP-003",
                name="Run Capacitor 40/5",
                description="Dual run capacitor 40/5 MFD 370V",
                manufacturer="GE",
                category="HVAC",
                quantity_available=12,
                unit_price=32.00,
                reorder_level=10,
            ),
            Part(
                id=uuid4(),
                part_number="HVAC-IGNITOR-001",
                name="Hot Surface Ignitor",
                description="Universal hot surface ignitor",
                manufacturer="White-Rodgers",
                category="HVAC",
                quantity_available=8,
                unit_price=45.00,
                reorder_level=5,
            ),
            Part(
                id=uuid4(),
                part_number="PLUMB-VALVE-001",
                name="Ball Valve 1/2 inch",
                description="Brass ball valve 1/2 inch",
                manufacturer="SharkBite",
                category="Plumbing",
                quantity_available=0,
                unit_price=18.50,
                reorder_level=5,
            ),
            Part(
                id=uuid4(),
                part_number="PLUMB-VALVE-002",
                name="Ball Valve 3/4 inch",
                description="Brass ball valve 3/4 inch",
                manufacturer="SharkBite",
                category="Plumbing",
                quantity_available=6,
                unit_price=22.00,
                reorder_level=5,
            ),
            Part(
                id=uuid4(),
                part_number="ELEC-BREAKER-001",
                name="Circuit Breaker 20A",
                description="Single pole 20A circuit breaker",
                manufacturer="Square D",
                category="Electrical",
                quantity_available=8,
                unit_price=12.00,
                reorder_level=5,
            ),
        ]
        
        for part in parts:
            db.add(part)
        
        db.commit()
        
        logger.info(f"Created {len(parts)} sample parts")
    
    finally:
        db.close()


async def example_check_parts_availability():
    """Example: Check parts availability."""
    logger.info("\n" + "="*60)
    logger.info("Example 1: Check Parts Availability")
    logger.info("="*60)
    
    # Create intake agent
    import os
    llm_client = UnifiedLLMClient(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "test-key"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
    agent = IntakeAgent(llm_client=llm_client)
    
    # Check availability for specific parts
    queries = [
        PartQuery(part_number="HVAC-THERM-001"),
        PartQuery(part_number="HVAC-CAP-002"),
        PartQuery(part_number="PLUMB-VALVE-001"),
    ]
    
    logger.info(f"Checking availability for {len(queries)} parts...")
    results = await agent.check_parts_availability(queries)
    
    for result in results:
        logger.info(f"\nPart: {result.name} ({result.part_number})")
        logger.info(f"  Available: {result.is_available}")
        logger.info(f"  Quantity: {result.quantity_available}")
        logger.info(f"  Reorder Needed: {result.reorder_needed}")
        if result.alternatives:
            logger.info(f"  Alternatives: {', '.join(result.alternatives)}")


async def example_search_parts():
    """Example: Search for parts."""
    logger.info("\n" + "="*60)
    logger.info("Example 2: Search Parts")
    logger.info("="*60)
    
    # Create intake agent
    import os
    llm_client = UnifiedLLMClient(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "test-key"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
    agent = IntakeAgent(llm_client=llm_client)
    
    # Search for capacitors
    logger.info("\nSearching for 'capacitor'...")
    results = await agent.search_parts("capacitor")
    
    logger.info(f"Found {len(results)} results:")
    for part in results:
        logger.info(f"  - {part['name']} ({part['part_number']})")
        logger.info(f"    Qty: {part['quantity_available']}, Price: ${part['unit_price']}")
    
    # Search in specific category
    logger.info("\nSearching for 'valve' in Plumbing category...")
    results = await agent.search_parts("valve", category="Plumbing")
    
    logger.info(f"Found {len(results)} results:")
    for part in results:
        logger.info(f"  - {part['name']} ({part['part_number']})")
        logger.info(f"    Qty: {part['quantity_available']}, Price: ${part['unit_price']}")


async def example_common_parts_for_service():
    """Example: Get common parts for service type."""
    logger.info("\n" + "="*60)
    logger.info("Example 3: Common Parts for Service Type")
    logger.info("="*60)
    
    # Create intake agent
    import os
    llm_client = UnifiedLLMClient(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "test-key"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
    agent = IntakeAgent(llm_client=llm_client)
    
    # Get common parts for HVAC
    logger.info("\nCommon parts for HVAC service:")
    parts = await agent.get_common_parts_for_service("HVAC")
    
    for part in parts:
        logger.info(f"  - {part.name} (Category: {part.category})")
    
    # Check availability of common parts
    logger.info("\nChecking availability of common HVAC parts...")
    availability = await agent.check_parts_availability(parts)
    
    available_count = sum(1 for p in availability if p.is_available)
    logger.info(f"Available: {available_count}/{len(availability)} parts in stock")


async def example_triage_with_parts_check():
    """Example: Triage lead with parts availability check."""
    logger.info("\n" + "="*60)
    logger.info("Example 4: Triage Lead with Parts Check")
    logger.info("="*60)
    
    # Create intake agent
    import os
    llm_client = UnifiedLLMClient(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "test-key"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
    agent = IntakeAgent(llm_client=llm_client)
    
    # Create test customer and lead
    db = next(get_db())
    
    try:
        # Create customer
        customer = Customer(
            id=uuid4(),
            name="John Smith",
            email="john.smith@example.com",
            phone="555-1234",
            address="123 Main St",
            city="Springfield",
            state="IL",
            zip_code="62701",
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        # Create lead
        lead = Lead(
            id=uuid4(),
            customer_id=customer.id,
            source="voice",
            urgency="urgent",
            service_type="HVAC",
            description="AC not cooling properly. Compressor runs but no cold air. Thermostat shows correct temperature.",
            status="new",
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        
        logger.info(f"\nTriaging lead: {lead.description}")
        
        # Triage the lead (includes parts check)
        result = await agent.triage_lead(lead)
        
        logger.info(f"\nTriage Result:")
        logger.info(f"  Service Type: {result.service_type}")
        logger.info(f"  Urgency: {result.urgency.value}")
        logger.info(f"  Priority: {result.priority}/10")
        logger.info(f"  Confidence: {result.confidence:.2%}")
        logger.info(f"  Estimated Duration: {result.estimated_duration} minutes")
        logger.info(f"  Required Skills: {', '.join(result.required_skills)}")
        logger.info(f"  Reasoning: {result.reasoning}")
    
    finally:
        db.close()


async def main():
    """Run all examples."""
    logger.info("Intake Agent Inventory Integration Examples")
    logger.info("=" * 60)
    
    # Setup sample parts
    await setup_sample_parts()
    
    # Run examples
    await example_check_parts_availability()
    await example_search_parts()
    await example_common_parts_for_service()
    await example_triage_with_parts_check()
    
    logger.info("\n" + "="*60)
    logger.info("All examples completed!")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())
