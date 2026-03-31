"""
Example usage of Intake Agent
Demonstrates lead capture, triage, and structured output extraction
"""

import asyncio
import os
from dotenv import load_dotenv

from backend.agents.intake import (
    IntakeAgent,
    LeadInput,
    LeadSource,
    CustomerInfo,
    create_intake_agent,
)
from backend.llm.unified_client import UnifiedLLMClient

# Load environment variables
load_dotenv()


async def example_voice_lead_capture():
    """Example: Capture lead from voice call."""
    print("\n" + "="*80)
    print("Example 1: Voice Lead Capture")
    print("="*80)
    
    # Initialize unified LLM client
    llm_client = UnifiedLLMClient(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        enable_logging=True,
    )
    
    # Create intake agent
    agent = create_intake_agent(llm_client=llm_client)
    
    # Simulate voice transcription
    voice_transcription = (
        "Hi, this is John Doe calling from 123 Main Street. "
        "My furnace stopped working last night and the house is freezing. "
        "It's really cold and I need someone to come out as soon as possible. "
        "My phone number is 555-1234 and email is john@example.com."
    )
    
    # Create lead input
    lead_input = LeadInput(
        source=LeadSource.VOICE,
        customer_info=CustomerInfo(
            name="John Doe",
            email="john@example.com",
            phone="555-1234",
            address="123 Main Street"
        ),
        issue_description="Furnace stopped working, house is freezing",
        raw_text=voice_transcription,
    )
    
    print(f"\nVoice Transcription:\n{voice_transcription}\n")
    
    # Capture lead
    print("Capturing lead...")
    lead = await agent.capture_lead(lead_input)
    
    print(f"\nLead Captured:")
    print(f"  ID: {lead.id}")
    print(f"  Source: {lead.source}")
    print(f"  Service Type: {lead.service_type}")
    print(f"  Urgency: {lead.urgency}")
    print(f"  Status: {lead.status}")
    
    # Triage lead
    print("\nTriaging lead...")
    triage_result = await agent.triage_lead(lead)
    
    print(f"\nTriage Result:")
    print(f"  Service Type: {triage_result.service_type}")
    print(f"  Urgency: {triage_result.urgency}")
    print(f"  Priority: {triage_result.priority}/10")
    print(f"  Estimated Duration: {triage_result.estimated_duration} minutes")
    print(f"  Required Skills: {', '.join(triage_result.required_skills)}")
    print(f"  Confidence: {triage_result.confidence:.2%}")
    print(f"  Reasoning: {triage_result.reasoning[:200]}...")
    
    # Show statistics
    stats = agent.get_statistics()
    print(f"\nAgent Statistics:")
    print(f"  Total Leads: {stats['total_leads']}")
    print(f"  Successful Triages: {stats['successful_triages']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")


async def example_web_lead_capture():
    """Example: Capture lead from web form."""
    print("\n" + "="*80)
    print("Example 2: Web Lead Capture")
    print("="*80)
    
    # Initialize unified LLM client
    llm_client = UnifiedLLMClient(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        enable_logging=True,
    )
    
    # Create intake agent
    agent = create_intake_agent(llm_client=llm_client)
    
    # Simulate web form submission
    web_form_data = {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "555-5678",
        "address": "456 Oak Avenue",
        "issue": "Kitchen sink is leaking under the cabinet. Water is dripping constantly."
    }
    
    # Create lead input
    lead_input = LeadInput(
        source=LeadSource.WEB,
        customer_info=CustomerInfo(
            name=web_form_data["name"],
            email=web_form_data["email"],
            phone=web_form_data["phone"],
            address=web_form_data["address"]
        ),
        issue_description=web_form_data["issue"],
        raw_text=web_form_data["issue"],
    )
    
    print(f"\nWeb Form Submission:")
    print(f"  Name: {web_form_data['name']}")
    print(f"  Email: {web_form_data['email']}")
    print(f"  Issue: {web_form_data['issue']}\n")
    
    # Capture and triage
    print("Capturing and triaging lead...")
    lead = await agent.capture_lead(lead_input)
    triage_result = await agent.triage_lead(lead)
    
    print(f"\nTriage Result:")
    print(f"  Service Type: {triage_result.service_type}")
    print(f"  Urgency: {triage_result.urgency}")
    print(f"  Priority: {triage_result.priority}/10")
    print(f"  Estimated Duration: {triage_result.estimated_duration} minutes")


async def example_sms_lead_capture():
    """Example: Capture lead from SMS."""
    print("\n" + "="*80)
    print("Example 3: SMS Lead Capture")
    print("="*80)
    
    # Initialize unified LLM client
    llm_client = UnifiedLLMClient(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        enable_logging=True,
    )
    
    # Create intake agent
    agent = create_intake_agent(llm_client=llm_client)
    
    # Simulate SMS message
    sms_message = "AC not cooling. Need repair ASAP. 555-9012"
    
    # Create lead input
    lead_input = LeadInput(
        source=LeadSource.SMS,
        customer_info=CustomerInfo(
            phone="555-9012"
        ),
        issue_description="AC not cooling",
        raw_text=sms_message,
    )
    
    print(f"\nSMS Message: {sms_message}\n")
    
    # Capture and triage
    print("Capturing and triaging lead...")
    lead = await agent.capture_lead(lead_input)
    triage_result = await agent.triage_lead(lead)
    
    print(f"\nTriage Result:")
    print(f"  Service Type: {triage_result.service_type}")
    print(f"  Urgency: {triage_result.urgency}")
    print(f"  Priority: {triage_result.priority}/10")


async def example_structured_extraction():
    """Example: Structured data extraction with PydanticAI."""
    print("\n" + "="*80)
    print("Example 4: Structured Data Extraction")
    print("="*80)
    
    # Initialize unified LLM client
    llm_client = UnifiedLLMClient(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        enable_logging=True,
    )
    
    # Create intake agent
    agent = create_intake_agent(llm_client=llm_client)
    
    # Unstructured text
    unstructured_text = (
        "My water heater is making loud banging noises and the water isn't getting hot. "
        "It's a gas water heater, about 10 years old. The pilot light is on but something "
        "seems wrong. This is not an emergency but I'd like someone to look at it soon."
    )
    
    print(f"\nUnstructured Text:\n{unstructured_text}\n")
    
    # Extract structured data
    print("Extracting structured data...")
    from backend.agents.intake import StructuredLeadData
    
    structured_data = await agent.extract_structured_data(
        text=unstructured_text,
        schema=StructuredLeadData
    )
    
    print(f"\nExtracted Structured Data:")
    print(f"  Service Type: {structured_data.service_type}")
    print(f"  Urgency: {structured_data.urgency}")
    print(f"  Issue Summary: {structured_data.issue_summary}")
    print(f"  Equipment Type: {structured_data.equipment_type}")
    print(f"  Symptoms: {', '.join(structured_data.symptoms)}")


async def example_multi_source_workflow():
    """Example: Handle multiple leads from different sources."""
    print("\n" + "="*80)
    print("Example 5: Multi-Source Workflow")
    print("="*80)
    
    # Initialize unified LLM client
    llm_client = UnifiedLLMClient(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        enable_logging=True,
    )
    
    # Create intake agent
    agent = create_intake_agent(llm_client=llm_client)
    
    # Multiple leads from different sources
    leads_data = [
        {
            "source": LeadSource.VOICE,
            "customer": CustomerInfo(name="Alice", phone="555-1111"),
            "issue": "Electrical outlet sparking",
        },
        {
            "source": LeadSource.WEB,
            "customer": CustomerInfo(name="Bob", email="bob@example.com"),
            "issue": "Dishwasher not draining",
        },
        {
            "source": LeadSource.SMS,
            "customer": CustomerInfo(phone="555-3333"),
            "issue": "Toilet running constantly",
        },
    ]
    
    print("\nProcessing multiple leads from different sources...\n")
    
    for i, lead_data in enumerate(leads_data, 1):
        print(f"Lead {i}: {lead_data['source'].value} - {lead_data['issue']}")
        
        lead_input = LeadInput(
            source=lead_data["source"],
            customer_info=lead_data["customer"],
            issue_description=lead_data["issue"],
            raw_text=lead_data["issue"],
        )
        
        lead = await agent.capture_lead(lead_input)
        triage_result = await agent.triage_lead(lead)
        
        print(f"  → Triaged as {triage_result.urgency.value} "
              f"({triage_result.service_type}, Priority: {triage_result.priority})")
    
    # Show final statistics
    stats = agent.get_statistics()
    print(f"\nFinal Statistics:")
    print(f"  Total Leads Processed: {stats['total_leads']}")
    print(f"  Successful Triages: {stats['successful_triages']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")


async def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("INTAKE AGENT EXAMPLES")
    print("="*80)
    
    try:
        await example_voice_lead_capture()
        await example_web_lead_capture()
        await example_sms_lead_capture()
        await example_structured_extraction()
        await example_multi_source_workflow()
        
        print("\n" + "="*80)
        print("All examples completed successfully!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
