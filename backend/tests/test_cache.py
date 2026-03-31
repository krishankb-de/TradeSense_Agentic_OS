"""Unit tests for Redis caching layer."""

import pytest
from unittest.mock import Mock, patch
import json

from backend.db.cache import (
    RedisCache,
    CacheManager,
    CACHE_TTL_SESSION_STATE,
    CACHE_TTL_TECHNICIAN_SCHEDULE,
    CACHE_TTL_CUSTOMER_DATA,
    CACHE_TTL_PARTS_INVENTORY,
)


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    with patch("backend.db.cache.redis.Redis") as mock:
        yield mock.return_value


@pytest.fixture
def redis_cache(mock_redis):
    """Create RedisCache instance with mocked Redis."""
    with patch("backend.db.cache.ConnectionPool"):
        cache = RedisCache()
        cache.client = mock_redis
        return cache


@pytest.fixture
def cache_manager(redis_cache):
    """Create CacheManager instance."""
    return CacheManager(redis_cache)


# RedisCache Tests
def test_redis_cache_get_success(redis_cache, mock_redis):
    """Test successful cache get."""
    test_data = {"key": "value", "number": 42}
    mock_redis.get.return_value = json.dumps(test_data)
    
    result = redis_cache.get("test_key")
    assert result == test_data
    mock_redis.get.assert_called_once_with("test_key")


def test_redis_cache_get_not_found(redis_cache, mock_redis):
    """Test cache get when key not found."""
    mock_redis.get.return_value = None
    
    result = redis_cache.get("nonexistent")
    assert result is None


def test_redis_cache_get_json_error(redis_cache, mock_redis):
    """Test cache get with invalid JSON."""
    mock_redis.get.return_value = "invalid json"
    
    result = redis_cache.get("test_key")
    assert result is None


def test_redis_cache_set_success(redis_cache, mock_redis):
    """Test successful cache set."""
    test_data = {"key": "value"}
    mock_redis.setex.return_value = True
    
    result = redis_cache.set("test_key", test_data, ttl=300)
    assert result is True
    mock_redis.setex.assert_called_once()
    
    # Verify serialization
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "test_key"
    assert call_args[0][1] == 300
    assert json.loads(call_args[0][2]) == test_data


def test_redis_cache_set_default_ttl(redis_cache, mock_redis):
    """Test cache set with default TTL."""
    mock_redis.setex.return_value = True
    
    redis_cache.set("test_key", {"data": "value"})
    
    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 3600  # Default TTL


def test_redis_cache_delete_success(redis_cache, mock_redis):
    """Test successful cache delete."""
    mock_redis.delete.return_value = 1
    
    result = redis_cache.delete("test_key")
    assert result is True
    mock_redis.delete.assert_called_once_with("test_key")


def test_redis_cache_delete_not_found(redis_cache, mock_redis):
    """Test cache delete when key not found."""
    mock_redis.delete.return_value = 0
    
    result = redis_cache.delete("nonexistent")
    assert result is False


def test_redis_cache_exists(redis_cache, mock_redis):
    """Test cache exists check."""
    mock_redis.exists.return_value = 1
    
    result = redis_cache.exists("test_key")
    assert result is True
    mock_redis.exists.assert_called_once_with("test_key")


def test_redis_cache_clear_pattern(redis_cache, mock_redis):
    """Test clear cache by pattern."""
    mock_redis.keys.return_value = ["key1", "key2", "key3"]
    mock_redis.delete.return_value = 3
    
    result = redis_cache.clear_pattern("session:*")
    assert result == 3
    mock_redis.keys.assert_called_once_with("session:*")
    mock_redis.delete.assert_called_once_with("key1", "key2", "key3")


def test_redis_cache_clear_pattern_no_keys(redis_cache, mock_redis):
    """Test clear pattern when no keys match."""
    mock_redis.keys.return_value = []
    
    result = redis_cache.clear_pattern("nonexistent:*")
    assert result == 0
    mock_redis.delete.assert_not_called()


def test_redis_cache_ping_success(redis_cache, mock_redis):
    """Test Redis ping success."""
    mock_redis.ping.return_value = True
    
    result = redis_cache.ping()
    assert result is True


def test_redis_cache_ping_failure(redis_cache, mock_redis):
    """Test Redis ping failure."""
    mock_redis.ping.side_effect = Exception("Connection failed")
    
    result = redis_cache.ping()
    assert result is False


# CacheManager Tests - Session State
def test_cache_manager_get_session_state(cache_manager, redis_cache, mock_redis):
    """Test get session state."""
    session_data = {"user_id": "123", "state": "active"}
    mock_redis.get.return_value = json.dumps(session_data)
    
    result = cache_manager.get_session_state("session-123")
    assert result == session_data
    mock_redis.get.assert_called_once_with("session:session-123")


def test_cache_manager_set_session_state(cache_manager, redis_cache, mock_redis):
    """Test set session state with correct TTL."""
    session_data = {"user_id": "123", "state": "active"}
    mock_redis.setex.return_value = True
    
    result = cache_manager.set_session_state("session-123", session_data)
    assert result is True
    
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "session:session-123"
    assert call_args[0][1] == CACHE_TTL_SESSION_STATE  # 15 minutes


def test_cache_manager_delete_session_state(cache_manager, redis_cache, mock_redis):
    """Test delete session state."""
    mock_redis.delete.return_value = 1
    
    result = cache_manager.delete_session_state("session-123")
    assert result is True
    mock_redis.delete.assert_called_once_with("session:session-123")


# CacheManager Tests - Technician Schedule
def test_cache_manager_get_technician_schedule(cache_manager, redis_cache, mock_redis):
    """Test get technician schedule."""
    schedule_data = {"jobs": [{"id": "job-1", "time": "10:00"}]}
    mock_redis.get.return_value = json.dumps(schedule_data)
    
    result = cache_manager.get_technician_schedule("tech-123")
    assert result == schedule_data


def test_cache_manager_set_technician_schedule(cache_manager, redis_cache, mock_redis):
    """Test set technician schedule with correct TTL."""
    schedule_data = {"jobs": []}
    mock_redis.setex.return_value = True
    
    result = cache_manager.set_technician_schedule("tech-123", schedule_data)
    assert result is True
    
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "schedule:technician:tech-123"
    assert call_args[0][1] == CACHE_TTL_TECHNICIAN_SCHEDULE  # 15 minutes


def test_cache_manager_invalidate_technician_schedule(cache_manager, redis_cache, mock_redis):
    """Test invalidate technician schedule."""
    mock_redis.delete.return_value = 1
    
    result = cache_manager.invalidate_technician_schedule("tech-123")
    assert result is True


def test_cache_manager_invalidate_all_schedules(cache_manager, redis_cache, mock_redis):
    """Test invalidate all technician schedules."""
    mock_redis.keys.return_value = ["schedule:technician:1", "schedule:technician:2"]
    mock_redis.delete.return_value = 2
    
    result = cache_manager.invalidate_all_schedules()
    assert result == 2
    mock_redis.keys.assert_called_once_with("schedule:technician:*")


# CacheManager Tests - Customer Data
def test_cache_manager_get_customer_data(cache_manager, redis_cache, mock_redis):
    """Test get customer data."""
    customer_data = {"name": "John Doe", "email": "john@example.com"}
    mock_redis.get.return_value = json.dumps(customer_data)
    
    result = cache_manager.get_customer_data("customer-123")
    assert result == customer_data


def test_cache_manager_set_customer_data(cache_manager, redis_cache, mock_redis):
    """Test set customer data with correct TTL."""
    customer_data = {"name": "John Doe"}
    mock_redis.setex.return_value = True
    
    result = cache_manager.set_customer_data("customer-123", customer_data)
    assert result is True
    
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "customer:customer-123"
    assert call_args[0][1] == CACHE_TTL_CUSTOMER_DATA  # 1 hour


def test_cache_manager_invalidate_customer_data(cache_manager, redis_cache, mock_redis):
    """Test invalidate customer data."""
    mock_redis.delete.return_value = 1
    
    result = cache_manager.invalidate_customer_data("customer-123")
    assert result is True


# CacheManager Tests - Parts Inventory
def test_cache_manager_get_part_inventory(cache_manager, redis_cache, mock_redis):
    """Test get part inventory."""
    inventory_data = {"quantity": 50, "location": "warehouse-A"}
    mock_redis.get.return_value = json.dumps(inventory_data)
    
    result = cache_manager.get_part_inventory("part-123")
    assert result == inventory_data


def test_cache_manager_set_part_inventory(cache_manager, redis_cache, mock_redis):
    """Test set part inventory with correct TTL."""
    inventory_data = {"quantity": 50}
    mock_redis.setex.return_value = True
    
    result = cache_manager.set_part_inventory("part-123", inventory_data)
    assert result is True
    
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "part:inventory:part-123"
    assert call_args[0][1] == CACHE_TTL_PARTS_INVENTORY  # 5 minutes


def test_cache_manager_invalidate_part_inventory(cache_manager, redis_cache, mock_redis):
    """Test invalidate part inventory."""
    mock_redis.delete.return_value = 1
    
    result = cache_manager.invalidate_part_inventory("part-123")
    assert result is True


def test_cache_manager_invalidate_all_parts(cache_manager, redis_cache, mock_redis):
    """Test invalidate all parts inventory."""
    mock_redis.keys.return_value = ["part:inventory:1", "part:inventory:2"]
    mock_redis.delete.return_value = 2
    
    result = cache_manager.invalidate_all_parts()
    assert result == 2


# CacheManager Tests - Conversation Context
def test_cache_manager_get_conversation_context(cache_manager, redis_cache, mock_redis):
    """Test get conversation context."""
    context_data = {"intent": "greeting", "entities": []}
    mock_redis.get.return_value = json.dumps(context_data)
    
    result = cache_manager.get_conversation_context("conv-123")
    assert result == context_data


def test_cache_manager_set_conversation_context(cache_manager, redis_cache, mock_redis):
    """Test set conversation context."""
    context_data = {"intent": "greeting"}
    mock_redis.setex.return_value = True
    
    result = cache_manager.set_conversation_context("conv-123", context_data)
    assert result is True
    
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "conversation:context:conv-123"


def test_cache_manager_delete_conversation_context(cache_manager, redis_cache, mock_redis):
    """Test delete conversation context."""
    mock_redis.delete.return_value = 1
    
    result = cache_manager.delete_conversation_context("conv-123")
    assert result is True
