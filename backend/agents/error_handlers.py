"""
Agent-specific Error Handlers.

Implements error handling for agent operations:
- Parts not found handling (search alternatives, provide lead time)
- Scheduling conflict handling (propose alternatives, re-optimize)

**Validates: Requirements 15.5, 15.6**
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from core.error_handling import (
    ErrorHandler,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    get_error_handler,
)

logger = logging.getLogger(__name__)


class PartNotFoundStrategy(Enum):
    """Strategies for handling parts not found."""
    SEARCH_ALTERNATIVES = "search_alternatives"
    ORDER_FROM_SUPPLIER = "order_from_supplier"
    CUSTOMER_SUPPLIED = "customer_supplied"
    CANCEL_JOB = "cancel_job"


@dataclass
class PartNotFoundContext:
    """Context for parts not found error."""
    part_id: str
    part_name: str
    job_id: str
    alternatives_found: List[Dict[str, Any]]
    lead_time_days: Optional[int] = None
    strategy: PartNotFoundStrategy = PartNotFoundStrategy.SEARCH_ALTERNATIVES


@dataclass
class SchedulingConflictContext:
    """Context for scheduling conflict."""
    job_id: str
    requested_time: str
    technician_id: Optional[str] = None
    conflict_reason: str = ""
    alternative_slots: List[Dict[str, Any]] = None
    is_emergency: bool = False


class PartsNotFoundHandler:
    """
    Handler for parts not found errors.
    
    Features:
    - Search for compatible alternatives
    - Provide estimated lead time for ordering
    - Update job status to 'parts-pending'
    - Notify customer and technician
    
    **Validates: Requirement 15.5**
    """
    
    def __init__(self):
        """Initialize parts not found handler."""
        self.error_handler = get_error_handler()
        self.handled_cases: List[PartNotFoundContext] = []
        logger.info("Parts not found handler initialized")
    
    async def handle_part_not_found(
        self,
        part_id: str,
        part_name: str,
        job_id: str,
        inventory_service: Optional[Any] = None,
    ) -> PartNotFoundContext:
        """
        Handle parts not found error.
        
        **Validates: Requirement 15.5**
        
        Args:
            part_id: Part ID that was not found
            part_name: Part name
            job_id: Job ID
            inventory_service: Optional inventory service for searching alternatives
            
        Returns:
            PartNotFoundContext with resolution strategy
        """
        logger.warning(f"Part not found: {part_name} (ID: {part_id}) for job {job_id}")
        
        # Log error
        error_context = ErrorContext(
            category=ErrorCategory.PARTS_NOT_FOUND,
            severity=ErrorSeverity.MEDIUM,
            message=f"Part not found: {part_name}",
            details={
                "part_id": part_id,
                "part_name": part_name,
                "job_id": job_id,
            },
        )
        self.error_handler.log_error(error_context)
        
        # Search for alternatives
        alternatives = await self._search_alternatives(
            part_id=part_id,
            part_name=part_name,
            inventory_service=inventory_service,
        )
        
        # Determine strategy
        if alternatives:
            strategy = PartNotFoundStrategy.SEARCH_ALTERNATIVES
            lead_time = None
            logger.info(f"Found {len(alternatives)} alternative parts")
        else:
            # Check if can order from supplier
            strategy = PartNotFoundStrategy.ORDER_FROM_SUPPLIER
            lead_time = await self._estimate_lead_time(part_id, part_name)
            logger.info(f"No alternatives found. Estimated lead time: {lead_time} days")
        
        # Create context
        context = PartNotFoundContext(
            part_id=part_id,
            part_name=part_name,
            job_id=job_id,
            alternatives_found=alternatives,
            lead_time_days=lead_time,
            strategy=strategy,
        )
        
        # Track handled case
        self.handled_cases.append(context)
        
        # Update job status
        await self._update_job_status(job_id, "parts-pending", context)
        
        return context
    
    async def _search_alternatives(
        self,
        part_id: str,
        part_name: str,
        inventory_service: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for compatible alternative parts.
        
        Args:
            part_id: Original part ID
            part_name: Original part name
            inventory_service: Optional inventory service
            
        Returns:
            List of alternative parts
        """
        alternatives = []
        
        # In a real implementation, this would:
        # 1. Query inventory for similar parts
        # 2. Check compatibility based on specifications
        # 3. Query Part-DB for alternatives
        # 4. Check distributor availability via KiCost
        
        # For now, simulate finding alternatives
        if "capacitor" in part_name.lower():
            alternatives = [
                {
                    "part_id": f"{part_id}_alt1",
                    "part_name": f"{part_name} (Alternative 1)",
                    "manufacturer": "Generic",
                    "in_stock": True,
                    "price": 2.50,
                    "compatibility": "compatible",
                },
                {
                    "part_id": f"{part_id}_alt2",
                    "part_name": f"{part_name} (Alternative 2)",
                    "manufacturer": "Brand X",
                    "in_stock": True,
                    "price": 3.00,
                    "compatibility": "compatible",
                },
            ]
        
        logger.debug(f"Found {len(alternatives)} alternatives for {part_name}")
        
        return alternatives
    
    async def _estimate_lead_time(
        self,
        part_id: str,
        part_name: str,
    ) -> int:
        """
        Estimate lead time for ordering part.
        
        Args:
            part_id: Part ID
            part_name: Part name
            
        Returns:
            Estimated lead time in days
        """
        # In a real implementation, this would:
        # 1. Query distributors for availability
        # 2. Check shipping times
        # 3. Consider supplier lead times
        
        # For now, return default estimate
        default_lead_time = 3  # 3 days
        
        logger.debug(f"Estimated lead time for {part_name}: {default_lead_time} days")
        
        return default_lead_time
    
    async def _update_job_status(
        self,
        job_id: str,
        status: str,
        context: PartNotFoundContext,
    ) -> None:
        """
        Update job status to parts-pending.
        
        Args:
            job_id: Job ID
            status: New status
            context: Part not found context
        """
        # In a real implementation, this would:
        # 1. Update job status in database
        # 2. Add notes about parts situation
        # 3. Notify customer and technician
        # 4. Schedule follow-up when parts arrive
        
        logger.info(
            f"Updated job {job_id} status to '{status}'. "
            f"Strategy: {context.strategy.value}"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get parts not found statistics.
        
        Returns:
            Dictionary with statistics
        """
        if not self.handled_cases:
            return {
                "total_cases": 0,
                "by_strategy": {},
                "average_lead_time": 0,
            }
        
        by_strategy = {}
        total_lead_time = 0
        lead_time_count = 0
        
        for case in self.handled_cases:
            strategy = case.strategy.value
            by_strategy[strategy] = by_strategy.get(strategy, 0) + 1
            
            if case.lead_time_days:
                total_lead_time += case.lead_time_days
                lead_time_count += 1
        
        avg_lead_time = total_lead_time / lead_time_count if lead_time_count > 0 else 0
        
        return {
            "total_cases": len(self.handled_cases),
            "by_strategy": by_strategy,
            "average_lead_time": avg_lead_time,
        }


class SchedulingConflictHandler:
    """
    Handler for scheduling conflicts.
    
    Features:
    - Propose alternative time slots
    - Re-run optimization with relaxed constraints
    - Escalate emergency jobs to on-call technician
    - Notify affected parties
    
    **Validates: Requirement 15.6**
    """
    
    def __init__(self):
        """Initialize scheduling conflict handler."""
        self.error_handler = get_error_handler()
        self.handled_conflicts: List[SchedulingConflictContext] = []
        logger.info("Scheduling conflict handler initialized")
    
    async def handle_scheduling_conflict(
        self,
        job_id: str,
        requested_time: str,
        technician_id: Optional[str] = None,
        conflict_reason: str = "",
        is_emergency: bool = False,
        scheduler_service: Optional[Any] = None,
    ) -> SchedulingConflictContext:
        """
        Handle scheduling conflict.
        
        **Validates: Requirement 15.6**
        
        Args:
            job_id: Job ID
            requested_time: Requested time slot
            technician_id: Optional technician ID
            conflict_reason: Reason for conflict
            is_emergency: Whether this is an emergency job
            scheduler_service: Optional scheduler service
            
        Returns:
            SchedulingConflictContext with resolution
        """
        logger.warning(
            f"Scheduling conflict for job {job_id}: {conflict_reason}. "
            f"Emergency: {is_emergency}"
        )
        
        # Log error
        severity = ErrorSeverity.HIGH if is_emergency else ErrorSeverity.MEDIUM
        error_context = ErrorContext(
            category=ErrorCategory.SCHEDULING_CONFLICT,
            severity=severity,
            message=f"Scheduling conflict: {conflict_reason}",
            details={
                "job_id": job_id,
                "requested_time": requested_time,
                "technician_id": technician_id,
                "is_emergency": is_emergency,
            },
        )
        self.error_handler.log_error(error_context)
        
        # Handle based on priority
        if is_emergency:
            # Escalate to on-call technician
            alternative_slots = await self._escalate_emergency(
                job_id=job_id,
                requested_time=requested_time,
            )
        else:
            # Propose alternative time slots
            alternative_slots = await self._propose_alternatives(
                job_id=job_id,
                requested_time=requested_time,
                technician_id=technician_id,
                scheduler_service=scheduler_service,
            )
        
        # Create context
        context = SchedulingConflictContext(
            job_id=job_id,
            requested_time=requested_time,
            technician_id=technician_id,
            conflict_reason=conflict_reason,
            alternative_slots=alternative_slots,
            is_emergency=is_emergency,
        )
        
        # Track handled conflict
        self.handled_conflicts.append(context)
        
        return context
    
    async def _propose_alternatives(
        self,
        job_id: str,
        requested_time: str,
        technician_id: Optional[str] = None,
        scheduler_service: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Propose alternative time slots.
        
        Args:
            job_id: Job ID
            requested_time: Requested time
            technician_id: Optional technician ID
            scheduler_service: Optional scheduler service
            
        Returns:
            List of alternative time slots
        """
        # In a real implementation, this would:
        # 1. Query scheduler for available slots
        # 2. Consider technician availability
        # 3. Re-run optimization with relaxed constraints
        # 4. Rank alternatives by convenience
        
        # For now, simulate alternatives
        alternatives = [
            {
                "time_slot": "2024-01-15 14:00",
                "technician_id": technician_id or "tech_001",
                "duration_minutes": 120,
                "confidence": 0.9,
            },
            {
                "time_slot": "2024-01-15 16:00",
                "technician_id": technician_id or "tech_002",
                "duration_minutes": 120,
                "confidence": 0.85,
            },
            {
                "time_slot": "2024-01-16 09:00",
                "technician_id": technician_id or "tech_001",
                "duration_minutes": 120,
                "confidence": 0.95,
            },
        ]
        
        logger.info(f"Proposed {len(alternatives)} alternative time slots for job {job_id}")
        
        return alternatives
    
    async def _escalate_emergency(
        self,
        job_id: str,
        requested_time: str,
    ) -> List[Dict[str, Any]]:
        """
        Escalate emergency job to on-call technician.
        
        Args:
            job_id: Job ID
            requested_time: Requested time
            
        Returns:
            List with on-call technician slot
        """
        # In a real implementation, this would:
        # 1. Find on-call technician
        # 2. Check immediate availability
        # 3. Bump lower-priority jobs if needed
        # 4. Send urgent notification
        
        # For now, simulate on-call assignment
        on_call_slot = [
            {
                "time_slot": requested_time,
                "technician_id": "tech_oncall",
                "duration_minutes": 120,
                "confidence": 1.0,
                "is_emergency": True,
                "bumped_jobs": [],  # Jobs that were rescheduled
            }
        ]
        
        logger.info(f"Escalated emergency job {job_id} to on-call technician")
        
        return on_call_slot
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get scheduling conflict statistics.
        
        Returns:
            Dictionary with statistics
        """
        if not self.handled_conflicts:
            return {
                "total_conflicts": 0,
                "emergency_count": 0,
                "resolution_rate": 0,
            }
        
        emergency_count = sum(1 for c in self.handled_conflicts if c.is_emergency)
        resolved_count = sum(
            1 for c in self.handled_conflicts
            if c.alternative_slots and len(c.alternative_slots) > 0
        )
        
        return {
            "total_conflicts": len(self.handled_conflicts),
            "emergency_count": emergency_count,
            "resolution_rate": resolved_count / len(self.handled_conflicts) * 100,
        }


# Global instances
_parts_handler = PartsNotFoundHandler()
_scheduling_handler = SchedulingConflictHandler()


def get_parts_not_found_handler() -> PartsNotFoundHandler:
    """Get global parts not found handler instance."""
    return _parts_handler


def get_scheduling_conflict_handler() -> SchedulingConflictHandler:
    """Get global scheduling conflict handler instance."""
    return _scheduling_handler
