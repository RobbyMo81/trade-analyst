"""Callback checker for OAuth and webhook validation"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class CallbackEvent:
    """Represents a callback event"""
    event_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    source: str
    status: str = 'pending'  # pending, processed, failed


class CallbackChecker:
    """Monitors and validates OAuth callbacks and webhooks"""
    
    def __init__(self, config: Config):
        self.config = config
        self.pending_callbacks = {}
        self.callback_history = []
        self.max_history = config.get('max_callback_history', 1000)
        self.callback_timeout = config.get('callback_timeout_seconds', 300)  # 5 minutes
        self.validators = {}
        self.handlers = {}
    
    def register_validator(self, event_type: str, validator: Callable[[Dict[str, Any]], bool]):
        """
        Register a validator function for a specific event type
        
        Args:
            event_type: Type of event to validate
            validator: Function that takes event data and returns bool
        """
        self.validators[event_type] = validator
        logger.info(f"Registered validator for event type: {event_type}")
    
    def register_handler(self, event_type: str, handler: Callable[[CallbackEvent], Any]):
        """
        Register a handler function for a specific event type
        
        Args:
            event_type: Type of event to handle
            handler: Function that processes the event
        """
        self.handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")
    
    async def expect_callback(self, 
                             event_id: str, 
                             event_type: str, 
                             source: str,
                             timeout_seconds: Optional[int] = None) -> bool:
        """
        Register expectation for a specific callback
        
        Args:
            event_id: Unique identifier for the expected callback
            event_type: Type of callback event
            source: Source of the callback (e.g., 'oauth', 'webhook')
            timeout_seconds: Optional timeout override
            
        Returns:
            bool: True if callback expectation was registered
        """
        try:
            timeout = timeout_seconds or self.callback_timeout
            expiry_time = datetime.now() + timedelta(seconds=timeout)
            
            self.pending_callbacks[event_id] = {
                'event_type': event_type,
                'source': source,
                'expected_at': datetime.now(),
                'expires_at': expiry_time,
                'status': 'waiting'
            }
            
            logger.info(f"Expecting callback: {event_id} ({event_type}) from {source}")
            
            # Start background task to clean up expired callbacks
            asyncio.create_task(self._cleanup_expired_callback(event_id, timeout))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register callback expectation: {e}")
            return False
    
    async def receive_callback(self, 
                              event_id: str, 
                              event_type: str, 
                              data: Dict[str, Any], 
                              source: str) -> bool:
        """
        Process a received callback
        
        Args:
            event_id: Unique identifier for the callback
            event_type: Type of callback event
            data: Callback data payload
            source: Source of the callback
            
        Returns:
            bool: True if callback was processed successfully
        """
        try:
            logger.info(f"Received callback: {event_id} ({event_type}) from {source}")
            
            # Create callback event
            callback_event = CallbackEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=datetime.now(),
                data=data,
                source=source
            )
            
            # Validate the callback
            if not await self._validate_callback(callback_event):
                logger.error(f"Callback validation failed: {event_id}")
                callback_event.status = 'failed'
                self._add_to_history(callback_event)
                return False
            
            # Check if this callback was expected
            if event_id in self.pending_callbacks:
                self.pending_callbacks[event_id]['status'] = 'received'
                logger.info(f"Expected callback received: {event_id}")
            else:
                logger.warning(f"Unexpected callback received: {event_id}")
            
            # Process the callback
            success = await self._process_callback(callback_event)
            
            if success:
                callback_event.status = 'processed'
                if event_id in self.pending_callbacks:
                    del self.pending_callbacks[event_id]
            else:
                callback_event.status = 'failed'
            
            self._add_to_history(callback_event)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to process callback {event_id}: {e}")
            return False
    
    async def wait_for_callback(self, event_id: str, timeout_seconds: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Wait for a specific callback to be received
        
        Args:
            event_id: ID of the callback to wait for
            timeout_seconds: Maximum time to wait
            
        Returns:
            Dict containing callback result or None if timeout
        """
        try:
            timeout = timeout_seconds or self.callback_timeout
            start_time = time.time()
            
            logger.info(f"Waiting for callback: {event_id} (timeout: {timeout}s)")
            
            while time.time() - start_time < timeout:
                # Check if callback was received
                if event_id not in self.pending_callbacks:
                    # Callback was processed, check history
                    for event in reversed(self.callback_history):
                        if event.event_id == event_id:
                            return {
                                'status': event.status,
                                'data': event.data,
                                'timestamp': event.timestamp.isoformat()
                            }
                
                # Check if callback is still pending
                pending = self.pending_callbacks.get(event_id)
                if pending and pending['status'] == 'received':
                    return {
                        'status': 'received',
                        'message': 'Callback received but not yet processed'
                    }
                
                await asyncio.sleep(0.5)  # Check every 500ms
            
            logger.warning(f"Callback timeout: {event_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for callback {event_id}: {e}")
            return None
    
    async def _validate_callback(self, callback_event: CallbackEvent) -> bool:
        """Validate a callback event"""
        try:
            # Check if we have a validator for this event type
            validator = self.validators.get(callback_event.event_type)
            if not validator:
                logger.warning(f"No validator registered for event type: {callback_event.event_type}")
                return True  # No validator means we accept it
            
            # Run the validator
            is_valid = validator(callback_event.data)
            
            if not is_valid:
                logger.error(f"Callback validation failed for {callback_event.event_id}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Callback validation error: {e}")
            return False
    
    async def _process_callback(self, callback_event: CallbackEvent) -> bool:
        """Process a callback event using registered handlers"""
        try:
            # Check if we have a handler for this event type
            handler = self.handlers.get(callback_event.event_type)
            if not handler:
                logger.warning(f"No handler registered for event type: {callback_event.event_type}")
                return True  # No handler means we consider it processed
            
            # Run the handler
            result = await handler(callback_event)
            
            if result is False:
                logger.error(f"Callback handler failed for {callback_event.event_id}")
                return False
            
            logger.info(f"Callback processed successfully: {callback_event.event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Callback processing error: {e}")
            return False
    
    async def _cleanup_expired_callback(self, event_id: str, timeout_seconds: int):
        """Clean up expired callback expectations"""
        try:
            await asyncio.sleep(timeout_seconds)
            
            if event_id in self.pending_callbacks:
                pending = self.pending_callbacks[event_id]
                if pending['status'] == 'waiting':
                    logger.warning(f"Callback expired: {event_id}")
                    pending['status'] = 'expired'
                    
                    # Remove from pending after a grace period
                    await asyncio.sleep(60)  # Keep for 1 minute after expiry
                    if event_id in self.pending_callbacks:
                        del self.pending_callbacks[event_id]
            
        except Exception as e:
            logger.error(f"Error cleaning up expired callback {event_id}: {e}")
    
    def _add_to_history(self, callback_event: CallbackEvent):
        """Add callback event to history"""
        self.callback_history.append(callback_event)
        
        # Keep history size under limit
        if len(self.callback_history) > self.max_history:
            self.callback_history = self.callback_history[-self.max_history:]
    
    def get_pending_callbacks(self) -> Dict[str, Dict[str, Any]]:
        """Get all pending callbacks"""
        return self.pending_callbacks.copy()
    
    def get_callback_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent callback history"""
        recent_events = self.callback_history[-limit:]
        
        return [
            {
                'event_id': event.event_id,
                'event_type': event.event_type,
                'timestamp': event.timestamp.isoformat(),
                'source': event.source,
                'status': event.status,
                'data_size': len(str(event.data))
            }
            for event in recent_events
        ]
    
    def get_callback_stats(self) -> Dict[str, Any]:
        """Get callback statistics"""
        total_callbacks = len(self.callback_history)
        
        if total_callbacks == 0:
            return {
                'total_callbacks': 0,
                'success_rate': 0,
                'pending_count': len(self.pending_callbacks)
            }
        
        successful = sum(1 for event in self.callback_history if event.status == 'processed')
        failed = sum(1 for event in self.callback_history if event.status == 'failed')
        
        # Count by event type
        event_type_counts = {}
        for event in self.callback_history:
            event_type_counts[event.event_type] = event_type_counts.get(event.event_type, 0) + 1
        
        return {
            'total_callbacks': total_callbacks,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total_callbacks) * 100,
            'pending_count': len(self.pending_callbacks),
            'event_type_counts': event_type_counts
        }


# Default validators
def oauth_callback_validator(data: Dict[str, Any]) -> bool:
    """Validate OAuth callback data"""
    required_fields = ['code', 'state']
    return all(field in data for field in required_fields)


def webhook_validator(data: Dict[str, Any]) -> bool:
    """Validate webhook data"""
    # Basic validation - should have some data
    return isinstance(data, dict) and len(data) > 0


# Example usage
async def main():
    """Example usage of CallbackChecker"""
    config = Config()
    checker = CallbackChecker(config)
    
    # Register validators
    checker.register_validator('oauth', oauth_callback_validator)
    checker.register_validator('webhook', webhook_validator)
    
    # Register handlers
    async def oauth_handler(event: CallbackEvent):
        print(f"Processing OAuth callback: {event.event_id}")
        return True
    
    checker.register_handler('oauth', oauth_handler)
    
    # Expect a callback
    await checker.expect_callback('oauth-123', 'oauth', 'provider')
    
    # Simulate receiving the callback
    await checker.receive_callback(
        'oauth-123', 
        'oauth', 
        {'code': 'abc123', 'state': 'xyz789'}, 
        'provider'
    )
    
    # Get statistics
    stats = checker.get_callback_stats()
    print(f"Callback stats: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
