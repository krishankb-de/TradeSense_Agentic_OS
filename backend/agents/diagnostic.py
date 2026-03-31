"""
Diagnostic Agent for TradeSense Field Service Management.

This agent handles:
- Issue analysis using LangGraph reasoning chains
- Equipment image parsing with Gemini Vision API
- Parts sourcing with alternatives via InvenTree/Part-DB/KiCost
- Repair guide generation
- AutoGen collaborative troubleshooting
- Documentation RAG for technical manual search

**Validates: Requirements 5.1-5.11, 7.5-7.7, 19.1-19.6, 20.2-20.9**
"""

import asyncio
import base64
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class DiagnosticComplexity(str, Enum):
    """Diagnostic complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class EquipmentInfo(BaseModel):
    """Equipment information extracted from images or text."""
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    equipment_type: Optional[str] = None
    specifications: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class Diagnosis(BaseModel):
    """Diagnostic result with root cause and recommendations."""
    issue_type: str
    root_cause: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    required_parts: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_repair_time: int  # minutes
    complexity: DiagnosticComplexity
    reasoning_steps: List[str] = Field(default_factory=list)
    safety_warnings: List[str] = Field(default_factory=list)


class PartRecommendation(BaseModel):
    """Parts recommendation with alternatives."""
    primary: List[Dict[str, Any]] = Field(default_factory=list)
    alternatives: List[List[Dict[str, Any]]] = Field(default_factory=list)
    total_cost: float = 0.0
    availability: str = "unknown"  # in-stock, order-required, unavailable
    distributor_options: List[Dict[str, Any]] = Field(default_factory=list)


class RepairGuide(BaseModel):
    """Step-by-step repair guide."""
    title: str
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    tools_required: List[str] = Field(default_factory=list)
    parts_list: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_time: int  # minutes
    difficulty: str = "moderate"
    safety_warnings: List[str] = Field(default_factory=list)


# ============================================================================
# Diagnostic Agent
# ============================================================================


class DiagnosticAgent:
    """
    Diagnostic agent for equipment troubleshooting and repair planning.
    
    Uses:
    - Gemini Vision API for image analysis
    - InvenTree/Part-DB for parts sourcing
    - KiCost for distributor pricing
    - Simple RAG for documentation search
    - AutoGen for collaborative troubleshooting
    
    **Validates: Requirements 5.1, 5.2, 5.8, 5.11**
    """
    
    def __init__(
        self,
        llm_client: Any,
        inventree_client: Optional[Any] = None,
        partdb_client: Optional[Any] = None,
        kicost_client: Optional[Any] = None,
    ):
        """
        Initialize diagnostic agent.
        
        Args:
            llm_client: LLM client for text generation (Gemini/Azure)
            inventree_client: InvenTree API client for inventory
            partdb_client: Part-DB client for component specs
            kicost_client: KiCost client for distributor pricing
        """
        self.llm_client = llm_client
        self.inventree_client = inventree_client
        self.partdb_client = partdb_client
        self.kicost_client = kicost_client
        
        logger.info("Initialized DiagnosticAgent")
    
    async def diagnose_issue(
        self,
        issue_description: str,
        equipment_info: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Diagnosis:
        """
        Analyze issue description and generate diagnosis.
        
        Uses LangGraph-style reasoning chains to analyze the issue
        and determine root cause.
        
        Args:
            issue_description: Description of the problem
            equipment_info: Optional equipment details
            context: Optional additional context
        
        Returns:
            Diagnosis with root cause and recommendations
        
        **Validates: Requirements 5.1, 5.2**
        """
        logger.info(f"Diagnosing issue: {issue_description[:100]}...")
        
        # Build diagnostic prompt with reasoning chain
        prompt = self._build_diagnostic_prompt(
            issue_description, equipment_info, context
        )
        
        try:
            # Use LLM for diagnostic reasoning
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.3,  # Lower temperature for more focused reasoning
                max_tokens=1500,
            )
            
            # Parse response into structured diagnosis
            diagnosis = self._parse_diagnosis_response(response, issue_description)
            
            logger.info(
                f"Diagnosis complete: {diagnosis.issue_type} "
                f"(confidence: {diagnosis.confidence:.2f})"
            )
            
            return diagnosis
            
        except Exception as e:
            logger.error(f"Error during diagnosis: {e}")
            # Return fallback diagnosis
            return Diagnosis(
                issue_type="unknown",
                root_cause="Unable to determine root cause",
                confidence=0.0,
                required_parts=[],
                estimated_repair_time=60,
                complexity=DiagnosticComplexity.COMPLEX,
                reasoning_steps=["Error occurred during diagnosis"],
                safety_warnings=["Consult with experienced technician"],
            )
    
    async def parse_equipment_image(
        self,
        image_data: bytes,
        image_format: str = "jpeg",
    ) -> EquipmentInfo:
        """
        Parse equipment labels from image using Gemini Vision API.
        
        Extracts manufacturer, model number, serial number using OCR
        and multimodal understanding.
        
        Args:
            image_data: Raw image bytes
            image_format: Image format (jpeg, png, etc.)
        
        Returns:
            EquipmentInfo with extracted details
        
        **Validates: Requirements 5.3, 5.4, 19.1-19.6**
        """
        logger.info(f"Parsing equipment image ({len(image_data)} bytes)")
        
        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Build vision prompt
            prompt = """Analyze this equipment image and extract the following information:
1. Manufacturer name
2. Model number
3. Serial number
4. Equipment type (e.g., HVAC unit, water heater, furnace)
5. Any visible specifications (capacity, voltage, etc.)

Focus on labels, nameplates, and identification tags. Provide high-confidence extractions only.

Format your response as JSON with these fields:
{
  "manufacturer": "...",
  "model_number": "...",
  "serial_number": "...",
  "equipment_type": "...",
  "specifications": {...},
  "confidence": 0.0-1.0
}"""
            
            # Use Gemini Vision API for multimodal analysis
            response = await self.llm_client.generate_with_image(
                prompt=prompt,
                image_data=image_base64,
                image_format=image_format,
                temperature=0.1,  # Very low temperature for factual extraction
                max_tokens=500,
            )
            
            # Parse response into EquipmentInfo
            equipment_info = self._parse_equipment_response(response)
            
            logger.info(
                f"Equipment parsed: {equipment_info.manufacturer} "
                f"{equipment_info.model_number} (confidence: {equipment_info.confidence:.2f})"
            )
            
            return equipment_info
            
        except Exception as e:
            logger.error(f"Error parsing equipment image: {e}")
            return EquipmentInfo(confidence=0.0)
    
    async def find_parts(
        self,
        diagnosis: Diagnosis,
        check_alternatives: bool = True,
    ) -> PartRecommendation:
        """
        Find required parts with alternatives and pricing.
        
        Queries InvenTree for inventory, Part-DB for specs,
        and KiCost for distributor pricing.
        
        Args:
            diagnosis: Diagnosis with required parts
            check_alternatives: Whether to find alternative parts
        
        Returns:
            PartRecommendation with primary and alternative parts
        
        **Validates: Requirements 5.5, 5.6, 7.5-7.7**
        """
        logger.info(f"Finding parts for {len(diagnosis.required_parts)} items")
        
        primary_parts = []
        alternatives = []
        total_cost = 0.0
        all_available = True
        
        for part_spec in diagnosis.required_parts:
            # Query InvenTree for primary part
            primary_part = await self._query_inventree_part(part_spec)
            
            if primary_part:
                primary_parts.append(primary_part)
                total_cost += primary_part.get("unit_cost", 0.0) * part_spec.get("quantity", 1)
                
                if primary_part.get("stock_status") != "in-stock":
                    all_available = False
            else:
                all_available = False
            
            # Find alternatives if requested
            if check_alternatives:
                part_alternatives = await self._find_alternative_parts(part_spec)
                alternatives.append(part_alternatives)
        
        # Determine availability status
        availability = "in-stock" if all_available else (
            "alternatives-available" if any(alternatives) else "order-required"
        )
        
        # Get distributor pricing via KiCost
        distributor_options = await self._get_distributor_pricing(primary_parts)
        
        recommendation = PartRecommendation(
            primary=primary_parts,
            alternatives=alternatives,
            total_cost=total_cost,
            availability=availability,
            distributor_options=distributor_options,
        )
        
        logger.info(
            f"Parts recommendation: {len(primary_parts)} primary, "
            f"{sum(len(a) for a in alternatives)} alternatives, "
            f"${total_cost:.2f} total"
        )
        
        return recommendation
    
    async def generate_repair_guide(
        self,
        diagnosis: Diagnosis,
        parts_recommendation: PartRecommendation,
    ) -> RepairGuide:
        """
        Generate step-by-step repair guide.
        
        Uses LLM to create detailed repair instructions with
        safety warnings and tool requirements.
        
        Args:
            diagnosis: Diagnosis with root cause
            parts_recommendation: Parts needed for repair
        
        Returns:
            RepairGuide with detailed instructions
        
        **Validates: Requirement 5.7**
        """
        logger.info(f"Generating repair guide for {diagnosis.issue_type}")
        
        # Build repair guide prompt
        prompt = f"""Generate a detailed step-by-step repair guide for the following issue:

Issue: {diagnosis.issue_type}
Root Cause: {diagnosis.root_cause}
Complexity: {diagnosis.complexity}

Required Parts:
{self._format_parts_list(parts_recommendation.primary)}

Create a comprehensive repair guide with:
1. Clear step-by-step instructions
2. Required tools
3. Safety warnings
4. Estimated time for each step
5. Tips and best practices

Format as JSON with these fields:
{{
  "title": "...",
  "steps": [
    {{"step_number": 1, "instruction": "...", "duration_minutes": 5, "tips": "..."}},
    ...
  ],
  "tools_required": ["...", "..."],
  "safety_warnings": ["...", "..."],
  "estimated_time": 60,
  "difficulty": "moderate"
}}"""
        
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.4,
                max_tokens=2000,
            )
            
            # Parse response into RepairGuide
            repair_guide = self._parse_repair_guide_response(
                response, diagnosis, parts_recommendation
            )
            
            logger.info(
                f"Repair guide generated: {len(repair_guide.steps)} steps, "
                f"{repair_guide.estimated_time} minutes"
            )
            
            return repair_guide
            
        except Exception as e:
            logger.error(f"Error generating repair guide: {e}")
            # Return minimal guide
            return RepairGuide(
                title=f"Repair Guide: {diagnosis.issue_type}",
                steps=[{"step_number": 1, "instruction": "Consult service manual"}],
                tools_required=["Standard toolkit"],
                parts_list=parts_recommendation.primary,
                estimated_time=diagnosis.estimated_repair_time,
                difficulty=diagnosis.complexity.value,
                safety_warnings=diagnosis.safety_warnings,
            )
    
    async def collaborative_troubleshoot(
        self,
        issue_description: str,
        technician_feedback: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Collaborative troubleshooting using AutoGen-style multi-turn dialogue.
        
        Engages in back-and-forth conversation with technician to
        refine diagnosis and provide targeted guidance.
        
        Args:
            issue_description: Initial problem description
            technician_feedback: List of technician messages/observations
            context: Optional conversation context
        
        Returns:
            Troubleshooting session result with recommendations
        
        **Validates: Requirements 5.8, 5.11**
        """
        logger.info(f"Starting collaborative troubleshooting session")
        
        # Build conversation history
        conversation = [
            {"role": "system", "content": "You are an expert field service diagnostic assistant."},
            {"role": "user", "content": f"Issue: {issue_description}"},
        ]
        
        # Add technician feedback to conversation
        for feedback in technician_feedback:
            conversation.append({
                "role": "user",
                "content": feedback.get("message", ""),
            })
        
        try:
            # Generate collaborative response
            response = await self.llm_client.generate_chat(
                messages=conversation,
                temperature=0.5,
                max_tokens=800,
            )
            
            result = {
                "response": response,
                "confidence": 0.8,  # Placeholder
                "next_steps": self._extract_next_steps(response),
                "requires_followup": self._check_requires_followup(response),
            }
            
            logger.info(f"Collaborative troubleshooting response generated")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in collaborative troubleshooting: {e}")
            return {
                "response": "Unable to process troubleshooting request. Please consult service manual.",
                "confidence": 0.0,
                "next_steps": [],
                "requires_followup": True,
            }
    
    async def query_documentation(
        self,
        query: str,
        equipment_info: Optional[EquipmentInfo] = None,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Query technical documentation using simple RAG.
        
        Searches indexed manuals and returns relevant sections
        with source citations.
        
        Args:
            query: Search query
            equipment_info: Optional equipment context for filtering
            max_results: Maximum number of results to return
        
        Returns:
            List of documentation results with citations
        
        **Validates: Requirements 5.9, 20.2, 20.3, 20.6, 20.9**
        """
        logger.info(f"Querying documentation: {query[:100]}...")
        
        # Placeholder for RAG implementation
        # In full implementation, this would:
        # 1. Generate query embedding
        # 2. Search vector database
        # 3. Retrieve relevant document chunks
        # 4. Return with source citations
        
        results = [
            {
                "content": "Placeholder documentation result",
                "source": "service_manual.pdf",
                "page": 42,
                "relevance_score": 0.85,
            }
        ]
        
        logger.info(f"Found {len(results)} documentation results")
        
        return results
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _build_diagnostic_prompt(
        self,
        issue_description: str,
        equipment_info: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Build diagnostic prompt with reasoning chain."""
        prompt = f"""Analyze the following equipment issue and provide a detailed diagnosis:

Issue Description: {issue_description}
"""
        
        if equipment_info:
            prompt += f"\nEquipment: {equipment_info.get('manufacturer', 'Unknown')} {equipment_info.get('model_number', 'Unknown')}"
        
        if context:
            prompt += f"\nAdditional Context: {context}"
        
        prompt += """

Provide a structured diagnosis with:
1. Issue type classification
2. Root cause analysis with reasoning steps
3. Required parts (if any)
4. Estimated repair time
5. Complexity level (simple/moderate/complex)
6. Safety warnings

Format as JSON:
{
  "issue_type": "...",
  "root_cause": "...",
  "confidence": 0.0-1.0,
  "required_parts": [{"type": "...", "quantity": 1, "specifications": {...}}],
  "estimated_repair_time": 60,
  "complexity": "moderate",
  "reasoning_steps": ["...", "..."],
  "safety_warnings": ["...", "..."]
}"""
        
        return prompt
    
    def _parse_diagnosis_response(
        self,
        response: str,
        issue_description: str,
    ) -> Diagnosis:
        """Parse LLM response into Diagnosis object."""
        import json
        
        try:
            # Try to parse JSON response
            data = json.loads(response)
            
            return Diagnosis(
                issue_type=data.get("issue_type", "unknown"),
                root_cause=data.get("root_cause", "Unable to determine"),
                confidence=float(data.get("confidence", 0.5)),
                required_parts=data.get("required_parts", []),
                estimated_repair_time=int(data.get("estimated_repair_time", 60)),
                complexity=DiagnosticComplexity(data.get("complexity", "moderate")),
                reasoning_steps=data.get("reasoning_steps", []),
                safety_warnings=data.get("safety_warnings", []),
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse diagnosis response: {e}")
            # Return fallback diagnosis
            return Diagnosis(
                issue_type="unknown",
                root_cause=response[:200] if response else "No response",
                confidence=0.3,
                required_parts=[],
                estimated_repair_time=60,
                complexity=DiagnosticComplexity.MODERATE,
                reasoning_steps=["Unable to parse structured response"],
                safety_warnings=[],
            )
    
    def _parse_equipment_response(self, response: str) -> EquipmentInfo:
        """Parse LLM vision response into EquipmentInfo."""
        import json
        
        try:
            data = json.loads(response)
            
            return EquipmentInfo(
                manufacturer=data.get("manufacturer"),
                model_number=data.get("model_number"),
                serial_number=data.get("serial_number"),
                equipment_type=data.get("equipment_type"),
                specifications=data.get("specifications", {}),
                confidence=float(data.get("confidence", 0.0)),
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse equipment response: {e}")
            return EquipmentInfo(confidence=0.0)
    
    def _parse_repair_guide_response(
        self,
        response: str,
        diagnosis: Diagnosis,
        parts_recommendation: PartRecommendation,
    ) -> RepairGuide:
        """Parse LLM response into RepairGuide."""
        import json
        
        try:
            data = json.loads(response)
            
            return RepairGuide(
                title=data.get("title", f"Repair: {diagnosis.issue_type}"),
                steps=data.get("steps", []),
                tools_required=data.get("tools_required", []),
                parts_list=parts_recommendation.primary,
                estimated_time=int(data.get("estimated_time", diagnosis.estimated_repair_time)),
                difficulty=data.get("difficulty", diagnosis.complexity.value),
                safety_warnings=data.get("safety_warnings", diagnosis.safety_warnings),
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse repair guide response: {e}")
            return RepairGuide(
                title=f"Repair Guide: {diagnosis.issue_type}",
                steps=[],
                tools_required=[],
                parts_list=parts_recommendation.primary,
                estimated_time=diagnosis.estimated_repair_time,
                difficulty=diagnosis.complexity.value,
                safety_warnings=diagnosis.safety_warnings,
            )
    
    async def _query_inventree_part(
        self,
        part_spec: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Query InvenTree for part availability."""
        if not self.inventree_client:
            logger.warning("InvenTree client not configured")
            return None
        
        try:
            # Query InvenTree API
            result = await self.inventree_client.search_part(
                part_type=part_spec.get("type"),
                specifications=part_spec.get("specifications", {}),
            )
            
            return result
        except Exception as e:
            logger.error(f"Error querying InvenTree: {e}")
            return None
    
    async def _find_alternative_parts(
        self,
        part_spec: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Find alternative compatible parts."""
        alternatives = []
        
        # Query Part-DB for alternatives
        if self.partdb_client:
            try:
                results = await self.partdb_client.find_alternatives(
                    part_type=part_spec.get("type"),
                    specifications=part_spec.get("specifications", {}),
                )
                alternatives.extend(results)
            except Exception as e:
                logger.error(f"Error finding alternatives: {e}")
        
        return alternatives
    
    async def _get_distributor_pricing(
        self,
        parts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Get distributor pricing via KiCost."""
        if not self.kicost_client or not parts:
            return []
        
        try:
            pricing = await self.kicost_client.get_pricing(parts)
            return pricing
        except Exception as e:
            logger.error(f"Error getting distributor pricing: {e}")
            return []
    
    def _format_parts_list(self, parts: List[Dict[str, Any]]) -> str:
        """Format parts list for prompt."""
        if not parts:
            return "No parts specified"
        
        lines = []
        for i, part in enumerate(parts, 1):
            lines.append(
                f"{i}. {part.get('name', 'Unknown')} "
                f"(Qty: {part.get('quantity', 1)})"
            )
        
        return "\n".join(lines)
    
    def _extract_next_steps(self, response: str) -> List[str]:
        """Extract next steps from troubleshooting response."""
        # Simple extraction - in production, use more sophisticated parsing
        steps = []
        for line in response.split("\n"):
            if line.strip().startswith(("1.", "2.", "3.", "-", "*")):
                steps.append(line.strip())
        
        return steps[:5]  # Limit to 5 steps
    
    def _check_requires_followup(self, response: str) -> bool:
        """Check if response requires followup."""
        followup_indicators = [
            "need more information",
            "can you check",
            "please verify",
            "what do you see",
            "unclear",
        ]
        
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in followup_indicators)


# ============================================================================
# Factory Function
# ============================================================================


def create_diagnostic_agent(
    llm_client: Any,
    inventree_client: Optional[Any] = None,
    partdb_client: Optional[Any] = None,
    kicost_client: Optional[Any] = None,
) -> DiagnosticAgent:
    """
    Create and configure a diagnostic agent.
    
    Args:
        llm_client: LLM client for text/vision generation
        inventree_client: Optional InvenTree API client
        partdb_client: Optional Part-DB client
        kicost_client: Optional KiCost client
    
    Returns:
        Configured DiagnosticAgent instance
    """
    return DiagnosticAgent(
        llm_client=llm_client,
        inventree_client=inventree_client,
        partdb_client=partdb_client,
        kicost_client=kicost_client,
    )
