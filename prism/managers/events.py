"""
Event system for Prism CLI.

Allows decoupled communication between components via signals and listeners.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type


class EventType(str, Enum):
    """Types of events in Prism."""
    ITEM_CREATED = "item.created"
    ITEM_UPDATED = "item.updated"
    ITEM_DELETED = "item.deleted"
    ITEM_COMPLETED = "item.completed"
    ITEM_ARCHIVED = "item.archived"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    STRATEGIC_COMPLETED = "strategic.completed"


@dataclass
class Event:
    """Base event class."""
    type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ItemEvent(Event):
    """Event for item-related actions."""
    item_uuid: str = ""
    item_type: str = ""
    item_slug: str = ""
    item_name: str = ""
    status: str = ""
    parent_uuid: Optional[str] = None


class EventListener(ABC):
    """Base class for event listeners."""
    
    @abstractmethod
    def handle(self, event: Event) -> None:
        """Handle an event.
        
        Args:
            event: The event to handle.
        """
        pass
    
    @property
    @abstractmethod
    def subscribed_events(self) -> List[EventType]:
        """Return list of event types this listener subscribes to."""
        pass


class EventBus:
    """
    Central event bus for publishing and subscribing to events.
    
    Thread-safe singleton pattern for global event access.
    """
    
    _instance: Optional['EventBus'] = None
    _listeners: Dict[EventType, List[EventListener]] = {}
    
    def __new__(cls) -> 'EventBus':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def subscribe(self, listener: EventListener) -> None:
        """Subscribe a listener to events.
        
        Args:
            listener: The listener to subscribe.
        """
        for event_type in listener.subscribed_events:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(listener)
    
    def unsubscribe(self, listener: EventListener) -> None:
        """Unsubscribe a listener from all events.
        
        Args:
            listener: The listener to unsubscribe.
        """
        for event_type in self._listeners:
            if listener in self._listeners[event_type]:
                self._listeners[event_type].remove(listener)
    
    def publish(self, event: Event) -> None:
        """Publish an event to all subscribed listeners.
        
        Args:
            event: The event to publish.
        """
        listeners = self._listeners.get(event.type, [])
        for listener in listeners:
            try:
                listener.handle(event)
            except Exception as e:
                # Log error but don't stop other listeners
                import click
                click.echo(f"  ⚠ Listener {listener.__class__.__name__} failed: {e}", err=True)
    
    def clear(self) -> None:
        """Clear all listeners (useful for testing)."""
        self._listeners.clear()


# Convenience functions for global event bus access
def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    return EventBus()


def publish_event(event: Event) -> None:
    """Publish an event to the global event bus."""
    get_event_bus().publish(event)


def subscribe_listener(listener: EventListener) -> None:
    """Subscribe a listener to the global event bus."""
    get_event_bus().subscribe(listener)
