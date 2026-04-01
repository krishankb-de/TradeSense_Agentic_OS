"""
WebSocket API for Real-Time Updates
Handles live notifications for technician and job status updates

Validates: Requirements 4.9
"""

import logging
import json
import asyncio
from typing import Dict, Set
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel

from security.auth import get_current_user_ws, User

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Connection Manager
# ============================================================================

class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    
    Features:
    - Per-user connection tracking
    - Broadcast to all connections
    - Targeted messages to specific users
    - Connection lifecycle management
    """
    
    def __init__(self):
        # Active connections: user_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
        # Connection metadata: websocket -> user info
        self.connection_metadata: Dict[WebSocket, dict] = {}
        
        logger.info("WebSocket ConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket, user: User):
        """
        Accept new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            user: Authenticated user
        """
        await websocket.accept()
        
        # Add to active connections
        if user.id not in self.active_connections:
            self.active_connections[user.id] = set()
        
        self.active_connections[user.id].add(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            'user_id': user.id,
            'user_email': user.email,
            'user_role': user.role,
            'connected_at': datetime.utcnow().isoformat()
        }
        
        logger.info(
            f"WebSocket connected: user={user.email}, "
            f"total_connections={self.get_connection_count()}"
        )
        
        # Send welcome message
        await self.send_personal_message(
            {
                'type': 'connected',
                'message': 'Connected to TradeSense real-time updates',
                'timestamp': datetime.utcnow().isoformat()
            },
            websocket
        )
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
        """
        # Get user info before removing
        metadata = self.connection_metadata.get(websocket, {})
        user_id = metadata.get('user_id')
        user_email = metadata.get('user_email', 'unknown')
        
        # Remove from active connections
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Remove user entry if no more connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove metadata
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
        
        logger.info(
            f"WebSocket disconnected: user={user_email}, "
            f"total_connections={self.get_connection_count()}"
        )
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to specific WebSocket connection.
        
        Args:
            message: Message dictionary
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
    
    async def send_to_user(self, message: dict, user_id: str):
        """
        Send message to all connections of a specific user.
        
        Args:
            message: Message dictionary
            user_id: Target user ID
        """
        if user_id not in self.active_connections:
            logger.warning(f"No active connections for user {user_id}")
            return
        
        # Send to all user's connections
        disconnected = []
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected clients.
        
        Args:
            message: Message dictionary
        """
        disconnected = []
        
        for user_id, websockets in self.active_connections.items():
            for websocket in websockets:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to user {user_id}: {e}")
                    disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_role(self, message: dict, role: str):
        """
        Broadcast message to all users with specific role.
        
        Args:
            message: Message dictionary
            role: Target role (e.g., 'technician', 'dispatcher')
        """
        disconnected = []
        
        for websocket, metadata in self.connection_metadata.items():
            if metadata.get('user_role') == role:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(
                        f"Failed to broadcast to role {role}: {e}"
                    )
                    disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
    
    def get_connection_count(self) -> int:
        """
        Get total number of active connections.
        
        Returns:
            Total connection count
        """
        return sum(len(websockets) for websockets in self.active_connections.values())
    
    def get_user_connection_count(self, user_id: str) -> int:
        """
        Get number of connections for specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            Connection count for user
        """
        return len(self.active_connections.get(user_id, set()))


# Global connection manager
manager = ConnectionManager()


# ============================================================================
# WebSocket Endpoints
# ============================================================================

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token")
):
    """
    WebSocket endpoint for real-time updates.
    
    Protocol:
    1. Client connects with JWT token in query parameter
    2. Server authenticates and accepts connection
    3. Server sends welcome message
    4. Client receives real-time updates:
       - Technician status changes
       - Job status updates
       - New lead notifications
       - Emergency alerts
    5. Client can send heartbeat messages to keep connection alive
    
    Message Types:
    - technician_status: Technician status changed
    - job_status: Job status updated
    - new_lead: New lead created
    - emergency_alert: Emergency job alert
    - heartbeat: Keep-alive message
    
    Validates: Requirement 4.9 (Real-time notifications)
    """
    try:
        # Authenticate user from token
        user = await get_current_user_ws(token)
        
        if not user:
            await websocket.close(code=1008, reason="Authentication failed")
            return
        
        # Accept connection
        await manager.connect(websocket, user)
        
        try:
            # Listen for messages
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    message_type = message.get('type')
                    
                    # Handle heartbeat
                    if message_type == 'heartbeat':
                        await manager.send_personal_message(
                            {
                                'type': 'heartbeat_ack',
                                'timestamp': datetime.utcnow().isoformat()
                            },
                            websocket
                        )
                    
                    # Handle other message types
                    elif message_type == 'ping':
                        await manager.send_personal_message(
                            {
                                'type': 'pong',
                                'timestamp': datetime.utcnow().isoformat()
                            },
                            websocket
                        )
                    
                    else:
                        logger.warning(
                            f"Unknown message type from user {user.email}: {message_type}"
                        )
                
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from user {user.email}: {data}")
                
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            logger.info(f"WebSocket disconnected: user={user.email}")
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass


# ============================================================================
# Helper Functions for Broadcasting Updates
# ============================================================================

async def broadcast_technician_status(
    technician_id: str,
    status: str,
    location: dict = None
):
    """
    Broadcast technician status update to all connected clients.
    
    Args:
        technician_id: Technician ID
        status: New status
        location: Optional location data
    """
    message = {
        'type': 'technician_status',
        'technician_id': technician_id,
        'status': status,
        'location': location,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    await manager.broadcast(message)
    logger.info(f"Broadcast technician status: {technician_id} -> {status}")


async def broadcast_job_status(
    job_id: str,
    status: str,
    technician_id: str = None,
    details: dict = None
):
    """
    Broadcast job status update to all connected clients.
    
    Args:
        job_id: Job ID
        status: New status
        technician_id: Optional technician ID
        details: Optional additional details
    """
    message = {
        'type': 'job_status',
        'job_id': job_id,
        'status': status,
        'technician_id': technician_id,
        'details': details or {},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    await manager.broadcast(message)
    logger.info(f"Broadcast job status: {job_id} -> {status}")


async def broadcast_new_lead(
    lead_id: str,
    urgency: str,
    service_type: str,
    customer_name: str
):
    """
    Broadcast new lead notification to dispatchers.
    
    Args:
        lead_id: Lead ID
        urgency: Lead urgency
        service_type: Service type
        customer_name: Customer name
    """
    message = {
        'type': 'new_lead',
        'lead_id': lead_id,
        'urgency': urgency,
        'service_type': service_type,
        'customer_name': customer_name,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Broadcast to dispatchers and admins
    await manager.broadcast_to_role(message, 'dispatcher')
    await manager.broadcast_to_role(message, 'admin')
    
    logger.info(f"Broadcast new lead: {lead_id} ({urgency})")


async def send_emergency_alert(
    job_id: str,
    location: str,
    description: str
):
    """
    Send emergency alert to all technicians.
    
    Args:
        job_id: Emergency job ID
        location: Emergency location
        description: Emergency description
    """
    message = {
        'type': 'emergency_alert',
        'job_id': job_id,
        'location': location,
        'description': description,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Broadcast to all technicians
    await manager.broadcast_to_role(message, 'technician')
    
    logger.warning(f"Emergency alert sent: {job_id} at {location}")


async def notify_technician(
    technician_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: dict = None
):
    """
    Send notification to specific technician.
    
    Args:
        technician_id: Technician user ID
        notification_type: Type of notification
        title: Notification title
        message: Notification message
        data: Optional additional data
    """
    notification = {
        'type': 'notification',
        'notification_type': notification_type,
        'title': title,
        'message': message,
        'data': data or {},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    await manager.send_to_user(notification, technician_id)
    logger.info(f"Notification sent to technician {technician_id}: {notification_type}")
