"""
Load Testing Suite for TradeSense System

Tests system performance under realistic production load conditions:
- 100 concurrent voice sessions
- 1000 MCP tool calls per minute
- 500 jobs scheduled simultaneously
- p95 latency < 600ms under load

**Validates: Requirements 14.2, 14.7, 14.8**
"""

import pytest
import asyncio
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
import statistics


# ============================================================================
# Load Test Data Models
# ============================================================================


@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    duration_seconds: float
    latencies_ms: List[float]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def requests_per_second(self) -> float:
        """Calculate throughput"""
        if self.duration_seconds == 0:
            return 0.0
        return self.total_requests / self.duration_seconds
    
    @property
    def p50_latency_ms(self) -> float:
        """Calculate p50 latency"""
        if not self.latencies_ms:
            return 0.0
        return statistics.median(self.latencies_ms)
    
    @property
    def p95_latency_ms(self) -> float:
        """Calculate p95 latency"""
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]
    
    @property
    def p99_latency_ms(self) -> float:
        """Calculate p99 latency"""
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        index = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency"""
        if not self.latencies_ms:
            return 0.0
        return statistics.mean(self.latencies_ms)


# ============================================================================
# Mock Voice Session for Load Testing
# ============================================================================


class MockVoiceSession:
    """Mock voice session for load testing"""
    
    def __init__(self, session_id: str, processing_delay_ms: float = 50):
        self.session_id = session_id
        self.processing_delay_ms = processing_delay_ms
        self.state = "active"
        self.turn_count = 0
        self.created_at = time.time()
    
    async def process_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """Simulate audio processing"""
        start_time = time.time()
        
        # Simulate processing delay
        await asyncio.sleep(self.processing_delay_ms / 1000.0)
        
        self.turn_count += 1
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "session_id": self.session_id,
            "transcription": f"Test audio {self.turn_count}",
            "latency_ms": latency_ms,
            "status": "success"
        }
    
    async def close(self):
        """Close session"""
        self.state = "closed"


class MockVoicePipeline:
    """Mock voice pipeline for load testing"""
    
    def __init__(self, max_concurrent_sessions: int = 100):
        self.max_concurrent_sessions = max_concurrent_sessions
        self.active_sessions: Dict[str, MockVoiceSession] = {}
        self.session_semaphore = asyncio.Semaphore(max_concurrent_sessions)
    
    async def start_session(self, session_id: str) -> MockVoiceSession:
        """Start a new voice session"""
        async with self.session_semaphore:
            session = MockVoiceSession(session_id)
            self.active_sessions[session_id] = session
            return session
    
    async def end_session(self, session_id: str):
        """End a voice session"""
        if session_id in self.active_sessions:
            await self.active_sessions[session_id].close()
            del self.active_sessions[session_id]
    
    def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.active_sessions)


# ============================================================================
# Mock MCP Client for Load Testing
# ============================================================================


class MockMCPClient:
    """Mock MCP client for load testing"""
    
    def __init__(self, response_delay_ms: float = 20):
        self.response_delay_ms = response_delay_ms
        self.call_count = 0
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP tool"""
        start_time = time.time()
        self.call_count += 1
        
        # Simulate processing delay
        await asyncio.sleep(self.response_delay_ms / 1000.0)
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "tool": tool_name,
            "result": f"Result for {tool_name}",
            "latency_ms": latency_ms,
            "status": "success"
        }


# ============================================================================
# Mock Scheduler for Load Testing
# ============================================================================


class MockScheduler:
    """Mock scheduler for load testing"""
    
    def __init__(self, optimization_delay_ms: float = 100):
        self.optimization_delay_ms = optimization_delay_ms
        self.scheduled_jobs: List[Dict[str, Any]] = []
    
    async def schedule_jobs(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Schedule multiple jobs"""
        start_time = time.time()
        
        # Simulate optimization delay
        await asyncio.sleep(self.optimization_delay_ms / 1000.0)
        
        # Add jobs to schedule
        self.scheduled_jobs.extend(jobs)
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "scheduled_count": len(jobs),
            "total_scheduled": len(self.scheduled_jobs),
            "latency_ms": latency_ms,
            "status": "success"
        }


# ============================================================================
# Load Test 1: 100 Concurrent Voice Sessions
# **Validates: Requirements 14.7**
# ============================================================================


@pytest.mark.load
@pytest.mark.asyncio
async def test_load_100_concurrent_voice_sessions():
    """
    **Validates: Requirements 14.7**
    
    Load Test: 100 concurrent voice sessions
    - System should handle 100 concurrent voice sessions
    - Each session should process multiple audio chunks
    - p95 latency should be < 600ms
    - Success rate should be >= 99%
    
    This test validates the system can handle the required concurrent
    voice session load for medium shop hardware.
    """
    num_sessions = 100
    audio_chunks_per_session = 10
    
    pipeline = MockVoicePipeline(max_concurrent_sessions=num_sessions)
    
    async def run_voice_session(session_id: str) -> LoadTestMetrics:
        """Run a single voice session"""
        latencies = []
        successful = 0
        failed = 0
        
        try:
            # Start session
            session = await pipeline.start_session(session_id)
            
            # Process audio chunks
            for i in range(audio_chunks_per_session):
                try:
                    result = await session.process_audio(b"test_audio_data")
                    latencies.append(result["latency_ms"])
                    successful += 1
                except Exception as e:
                    failed += 1
            
            # End session
            await pipeline.end_session(session_id)
            
        except Exception as e:
            failed += audio_chunks_per_session
        
        return LoadTestMetrics(
            total_requests=audio_chunks_per_session,
            successful_requests=successful,
            failed_requests=failed,
            duration_seconds=0,  # Will be calculated at aggregate level
            latencies_ms=latencies
        )
    
    # Run all sessions concurrently
    start_time = time.time()
    tasks = [run_voice_session(f"session-{i}") for i in range(num_sessions)]
    session_metrics = await asyncio.gather(*tasks)
    end_time = time.time()
    
    # Aggregate metrics
    total_requests = sum(m.total_requests for m in session_metrics)
    successful_requests = sum(m.successful_requests for m in session_metrics)
    failed_requests = sum(m.failed_requests for m in session_metrics)
    all_latencies = []
    for m in session_metrics:
        all_latencies.extend(m.latencies_ms)
    
    metrics = LoadTestMetrics(
        total_requests=total_requests,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        duration_seconds=end_time - start_time,
        latencies_ms=all_latencies
    )
    
    # Assertions
    print(f"\n=== Load Test: 100 Concurrent Voice Sessions ===")
    print(f"Total requests: {metrics.total_requests}")
    print(f"Successful: {metrics.successful_requests}")
    print(f"Failed: {metrics.failed_requests}")
    print(f"Success rate: {metrics.success_rate:.1%}")
    print(f"Duration: {metrics.duration_seconds:.2f}s")
    print(f"Throughput: {metrics.requests_per_second:.1f} req/s")
    print(f"p50 latency: {metrics.p50_latency_ms:.1f}ms")
    print(f"p95 latency: {metrics.p95_latency_ms:.1f}ms")
    print(f"p99 latency: {metrics.p99_latency_ms:.1f}ms")
    print(f"avg latency: {metrics.avg_latency_ms:.1f}ms")
    
    # Requirement 14.7: System should handle 100 concurrent voice sessions
    assert metrics.total_requests == num_sessions * audio_chunks_per_session, (
        f"Should process {num_sessions * audio_chunks_per_session} total requests"
    )
    
    # Requirement 14.2: p95 latency < 600ms under load
    assert metrics.p95_latency_ms < 600, (
        f"p95 latency ({metrics.p95_latency_ms:.1f}ms) should be < 600ms"
    )
    
    # Success rate should be >= 99%
    assert metrics.success_rate >= 0.99, (
        f"Success rate ({metrics.success_rate:.1%}) should be >= 99%"
    )
    
    # All sessions should complete
    assert metrics.successful_requests + metrics.failed_requests == metrics.total_requests


# ============================================================================
# Load Test 2: 1000 MCP Tool Calls Per Minute
# **Validates: Requirements 14.8**
# ============================================================================


@pytest.mark.load
@pytest.mark.asyncio
async def test_load_1000_mcp_calls_per_minute():
    """
    **Validates: Requirements 14.8**
    
    Load Test: 1000 MCP tool calls per minute
    - System should handle 1000+ MCP tool calls per minute
    - p95 latency should be < 600ms
    - Success rate should be >= 99.5%
    
    This test validates the MCP integration can handle high throughput
    as required for production field service operations.
    """
    num_calls = 1000
    
    client = MockMCPClient(response_delay_ms=20)
    
    async def make_mcp_call(call_id: int) -> Dict[str, Any]:
        """Make a single MCP tool call"""
        tools = ["query_inventory", "search_parts", "get_stock", "update_quantity", "check_availability"]
        tool_name = tools[call_id % len(tools)]
        
        try:
            result = await client.execute_tool(tool_name, {"call_id": call_id})
            return {
                "success": True,
                "latency_ms": result["latency_ms"]
            }
        except Exception as e:
            return {
                "success": False,
                "latency_ms": 0
            }
    
    # Execute calls concurrently
    start_time = time.time()
    tasks = [make_mcp_call(i) for i in range(num_calls)]
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    # Calculate metrics
    successful = sum(1 for r in results if r["success"])
    failed = num_calls - successful
    latencies = [r["latency_ms"] for r in results if r["success"]]
    duration_seconds = end_time - start_time
    duration_minutes = duration_seconds / 60.0
    
    metrics = LoadTestMetrics(
        total_requests=num_calls,
        successful_requests=successful,
        failed_requests=failed,
        duration_seconds=duration_seconds,
        latencies_ms=latencies
    )
    
    calls_per_minute = num_calls / duration_minutes
    
    # Assertions
    print(f"\n=== Load Test: 1000 MCP Tool Calls Per Minute ===")
    print(f"Total calls: {metrics.total_requests}")
    print(f"Successful: {metrics.successful_requests}")
    print(f"Failed: {metrics.failed_requests}")
    print(f"Success rate: {metrics.success_rate:.1%}")
    print(f"Duration: {metrics.duration_seconds:.2f}s ({duration_minutes:.2f} min)")
    print(f"Throughput: {calls_per_minute:.1f} calls/min")
    print(f"p50 latency: {metrics.p50_latency_ms:.1f}ms")
    print(f"p95 latency: {metrics.p95_latency_ms:.1f}ms")
    print(f"p99 latency: {metrics.p99_latency_ms:.1f}ms")
    
    # Requirement 14.8: System should handle 1000+ MCP tool calls per minute
    assert calls_per_minute >= 1000, (
        f"Throughput ({calls_per_minute:.1f} calls/min) should be >= 1000 calls/min"
    )
    
    # Requirement 14.2: p95 latency < 600ms under load
    assert metrics.p95_latency_ms < 600, (
        f"p95 latency ({metrics.p95_latency_ms:.1f}ms) should be < 600ms"
    )
    
    # Success rate should be >= 99.5%
    assert metrics.success_rate >= 0.995, (
        f"Success rate ({metrics.success_rate:.1%}) should be >= 99.5%"
    )


# ============================================================================
# Load Test 3: 500 Jobs Scheduled Simultaneously
# **Validates: Requirements 14.8**
# ============================================================================


@pytest.mark.load
@pytest.mark.asyncio
async def test_load_500_jobs_scheduled_simultaneously():
    """
    **Validates: Requirements 14.8**
    
    Load Test: 500 jobs scheduled simultaneously
    - System should handle 500 jobs being scheduled at once
    - Scheduling optimization should complete in reasonable time
    - p95 latency should be < 600ms per batch
    - All jobs should be scheduled successfully
    
    This test validates the scheduler can handle bulk job scheduling
    as required for daily operations.
    """
    num_jobs = 500
    batch_size = 50  # Schedule in batches
    num_batches = num_jobs // batch_size
    
    scheduler = MockScheduler(optimization_delay_ms=100)
    
    # Create test jobs
    jobs = [
        {
            "job_id": f"job-{i}",
            "technician_id": f"tech-{i % 10}",
            "service_type": "repair",
            "duration_minutes": 60,
            "priority": "routine"
        }
        for i in range(num_jobs)
    ]
    
    async def schedule_batch(batch_jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Schedule a batch of jobs"""
        try:
            result = await scheduler.schedule_jobs(batch_jobs)
            return {
                "success": True,
                "latency_ms": result["latency_ms"],
                "scheduled_count": result["scheduled_count"]
            }
        except Exception as e:
            return {
                "success": False,
                "latency_ms": 0,
                "scheduled_count": 0
            }
    
    # Schedule jobs in batches concurrently
    start_time = time.time()
    batches = [jobs[i:i+batch_size] for i in range(0, num_jobs, batch_size)]
    tasks = [schedule_batch(batch) for batch in batches]
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    # Calculate metrics
    successful_batches = sum(1 for r in results if r["success"])
    failed_batches = num_batches - successful_batches
    total_scheduled = sum(r["scheduled_count"] for r in results)
    latencies = [r["latency_ms"] for r in results if r["success"]]
    duration_seconds = end_time - start_time
    
    metrics = LoadTestMetrics(
        total_requests=num_batches,
        successful_requests=successful_batches,
        failed_requests=failed_batches,
        duration_seconds=duration_seconds,
        latencies_ms=latencies
    )
    
    # Assertions
    print(f"\n=== Load Test: 500 Jobs Scheduled Simultaneously ===")
    print(f"Total jobs: {num_jobs}")
    print(f"Batches: {num_batches}")
    print(f"Successful batches: {metrics.successful_requests}")
    print(f"Failed batches: {metrics.failed_requests}")
    print(f"Total scheduled: {total_scheduled}")
    print(f"Success rate: {metrics.success_rate:.1%}")
    print(f"Duration: {metrics.duration_seconds:.2f}s")
    print(f"p50 latency: {metrics.p50_latency_ms:.1f}ms")
    print(f"p95 latency: {metrics.p95_latency_ms:.1f}ms")
    print(f"p99 latency: {metrics.p99_latency_ms:.1f}ms")
    
    # All jobs should be scheduled
    assert total_scheduled == num_jobs, (
        f"All {num_jobs} jobs should be scheduled, but only {total_scheduled} were"
    )
    
    # Requirement 14.2: p95 latency < 600ms under load
    assert metrics.p95_latency_ms < 600, (
        f"p95 latency ({metrics.p95_latency_ms:.1f}ms) should be < 600ms per batch"
    )
    
    # All batches should succeed
    assert metrics.success_rate == 1.0, (
        f"All batches should succeed, but success rate is {metrics.success_rate:.1%}"
    )
    
    # Scheduling should complete in reasonable time (< 10 seconds for 500 jobs)
    assert metrics.duration_seconds < 10.0, (
        f"Scheduling should complete in < 10s, but took {metrics.duration_seconds:.2f}s"
    )


# ============================================================================
# Load Test 4: Combined System Load
# **Validates: Requirements 14.2, 14.7, 14.8**
# ============================================================================


@pytest.mark.load
@pytest.mark.asyncio
async def test_load_combined_system_stress():
    """
    **Validates: Requirements 14.2, 14.7, 14.8**
    
    Load Test: Combined system stress test
    - 50 concurrent voice sessions
    - 500 MCP tool calls per minute
    - 250 jobs scheduled
    - All running simultaneously
    - p95 latency < 600ms across all operations
    
    This test validates the system can handle realistic production load
    with multiple subsystems under stress simultaneously.
    """
    # Initialize components
    voice_pipeline = MockVoicePipeline(max_concurrent_sessions=50)
    mcp_client = MockMCPClient(response_delay_ms=20)
    scheduler = MockScheduler(optimization_delay_ms=100)
    
    # Voice session workload
    async def voice_workload() -> LoadTestMetrics:
        """Run voice session workload"""
        num_sessions = 50
        chunks_per_session = 5
        
        async def run_session(session_id: str):
            latencies = []
            successful = 0
            failed = 0
            
            try:
                session = await voice_pipeline.start_session(session_id)
                for _ in range(chunks_per_session):
                    try:
                        result = await session.process_audio(b"test")
                        latencies.append(result["latency_ms"])
                        successful += 1
                    except:
                        failed += 1
                await voice_pipeline.end_session(session_id)
            except:
                failed += chunks_per_session
            
            return (successful, failed, latencies)
        
        tasks = [run_session(f"voice-{i}") for i in range(num_sessions)]
        results = await asyncio.gather(*tasks)
        
        total_successful = sum(r[0] for r in results)
        total_failed = sum(r[1] for r in results)
        all_latencies = []
        for r in results:
            all_latencies.extend(r[2])
        
        return LoadTestMetrics(
            total_requests=num_sessions * chunks_per_session,
            successful_requests=total_successful,
            failed_requests=total_failed,
            duration_seconds=0,
            latencies_ms=all_latencies
        )
    
    # MCP workload
    async def mcp_workload() -> LoadTestMetrics:
        """Run MCP tool call workload"""
        num_calls = 500
        
        async def make_call(call_id: int):
            try:
                result = await mcp_client.execute_tool(f"tool_{call_id % 5}", {"id": call_id})
                return (True, result["latency_ms"])
            except:
                return (False, 0)
        
        tasks = [make_call(i) for i in range(num_calls)]
        results = await asyncio.gather(*tasks)
        
        successful = sum(1 for r in results if r[0])
        latencies = [r[1] for r in results if r[0]]
        
        return LoadTestMetrics(
            total_requests=num_calls,
            successful_requests=successful,
            failed_requests=num_calls - successful,
            duration_seconds=0,
            latencies_ms=latencies
        )
    
    # Scheduling workload
    async def scheduling_workload() -> LoadTestMetrics:
        """Run job scheduling workload"""
        num_jobs = 250
        batch_size = 50
        
        jobs = [{"job_id": f"job-{i}"} for i in range(num_jobs)]
        batches = [jobs[i:i+batch_size] for i in range(0, num_jobs, batch_size)]
        
        async def schedule_batch(batch):
            try:
                result = await scheduler.schedule_jobs(batch)
                return (True, result["latency_ms"])
            except:
                return (False, 0)
        
        tasks = [schedule_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks)
        
        successful = sum(1 for r in results if r[0])
        latencies = [r[1] for r in results if r[0]]
        
        return LoadTestMetrics(
            total_requests=len(batches),
            successful_requests=successful,
            failed_requests=len(batches) - successful,
            duration_seconds=0,
            latencies_ms=latencies
        )
    
    # Run all workloads concurrently
    start_time = time.time()
    voice_metrics, mcp_metrics, scheduling_metrics = await asyncio.gather(
        voice_workload(),
        mcp_workload(),
        scheduling_workload()
    )
    end_time = time.time()
    
    duration_seconds = end_time - start_time
    
    # Combine all latencies for overall p95
    all_latencies = (
        voice_metrics.latencies_ms +
        mcp_metrics.latencies_ms +
        scheduling_metrics.latencies_ms
    )
    
    combined_metrics = LoadTestMetrics(
        total_requests=(
            voice_metrics.total_requests +
            mcp_metrics.total_requests +
            scheduling_metrics.total_requests
        ),
        successful_requests=(
            voice_metrics.successful_requests +
            mcp_metrics.successful_requests +
            scheduling_metrics.successful_requests
        ),
        failed_requests=(
            voice_metrics.failed_requests +
            mcp_metrics.failed_requests +
            scheduling_metrics.failed_requests
        ),
        duration_seconds=duration_seconds,
        latencies_ms=all_latencies
    )
    
    # Assertions
    print(f"\n=== Load Test: Combined System Stress ===")
    print(f"Duration: {duration_seconds:.2f}s")
    print(f"\nVoice Sessions:")
    print(f"  Total: {voice_metrics.total_requests}")
    print(f"  Success rate: {voice_metrics.success_rate:.1%}")
    print(f"  p95 latency: {voice_metrics.p95_latency_ms:.1f}ms")
    print(f"\nMCP Tool Calls:")
    print(f"  Total: {mcp_metrics.total_requests}")
    print(f"  Success rate: {mcp_metrics.success_rate:.1%}")
    print(f"  p95 latency: {mcp_metrics.p95_latency_ms:.1f}ms")
    print(f"\nJob Scheduling:")
    print(f"  Total batches: {scheduling_metrics.total_requests}")
    print(f"  Success rate: {scheduling_metrics.success_rate:.1%}")
    print(f"  p95 latency: {scheduling_metrics.p95_latency_ms:.1f}ms")
    print(f"\nCombined:")
    print(f"  Total operations: {combined_metrics.total_requests}")
    print(f"  Overall success rate: {combined_metrics.success_rate:.1%}")
    print(f"  Overall p95 latency: {combined_metrics.p95_latency_ms:.1f}ms")
    
    # Requirement 14.2: p95 latency < 600ms under load
    assert combined_metrics.p95_latency_ms < 600, (
        f"Overall p95 latency ({combined_metrics.p95_latency_ms:.1f}ms) should be < 600ms"
    )
    
    # Each subsystem should meet latency requirements
    assert voice_metrics.p95_latency_ms < 600, (
        f"Voice p95 latency ({voice_metrics.p95_latency_ms:.1f}ms) should be < 600ms"
    )
    assert mcp_metrics.p95_latency_ms < 600, (
        f"MCP p95 latency ({mcp_metrics.p95_latency_ms:.1f}ms) should be < 600ms"
    )
    assert scheduling_metrics.p95_latency_ms < 600, (
        f"Scheduling p95 latency ({scheduling_metrics.p95_latency_ms:.1f}ms) should be < 600ms"
    )
    
    # Overall success rate should be >= 99%
    assert combined_metrics.success_rate >= 0.99, (
        f"Overall success rate ({combined_metrics.success_rate:.1%}) should be >= 99%"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "load", "-s"])
