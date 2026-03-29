import pytest
from prism.models.archived import ArchivedItem
from prism.models.base import Phase, ItemStatus

def test_archived_item_status_delegation():
    """ArchivedItem status property delegates to wrapped item."""
    phase = Phase(name="Test", slug="test", status=ItemStatus.COMPLETED)
    # Note: normally ArchiveManager sets status to ARCHIVED when archiving
    phase.status = ItemStatus.ARCHIVED
    
    archived = ArchivedItem.from_wrapped_item(phase)
    assert archived.status == ItemStatus.ARCHIVED
    assert archived.get_status() == ItemStatus.ARCHIVED

def test_archived_item_set_status_fails():
    """ArchivedItem set_status always raises ValueError."""
    phase = Phase(name="Test", slug="test", status=ItemStatus.ARCHIVED)
    archived = ArchivedItem.from_wrapped_item(phase)
    
    with pytest.raises(ValueError, match="Invalid status transition from 'archived'"):
        archived.set_status(ItemStatus.IN_PROGRESS)

def test_archived_item_model_dump():
    """ArchivedItem model_dump delegates to wrapped item."""
    phase = Phase(name="Test", slug="test", status=ItemStatus.ARCHIVED, description="Desc")
    archived = ArchivedItem.from_wrapped_item(phase)
    
    dump = archived.model_dump()
    assert dump["name"] == "Test"
    assert dump["slug"] == "test"
    assert dump["status"] == ItemStatus.ARCHIVED
    assert dump["description"] == "Desc"
    
    json_dump = archived.model_dump(mode="json")
    assert json_dump["status"] == "archived"
