from app.notifications import NotificationOutbox
from app.reminders import ReminderStore


def test_due_reminders_are_enqueued_once(tmp_path):
    db = tmp_path / "vayu.db"
    reminder_store = ReminderStore(str(db))
    outbox = NotificationOutbox(str(db))
    reminder_store.add("review CI", "2020-01-01T00:00:00Z")

    created = outbox.enqueue_due(reminder_store)
    duplicate = outbox.enqueue_due(reminder_store)

    assert len(created) == 1
    assert created[0]["message"] == "review CI"
    assert created[0]["status"] == "pending"
    assert duplicate == []
    assert len(outbox.list()) == 1


def test_future_reminder_is_not_enqueued(tmp_path):
    db = tmp_path / "vayu.db"
    reminder_store = ReminderStore(str(db))
    outbox = NotificationOutbox(str(db))
    reminder_store.add("future work", "2099-01-01T00:00:00Z")

    assert outbox.enqueue_due(reminder_store) == []


def test_outbox_persists_across_instances(tmp_path):
    db = tmp_path / "vayu.db"
    reminder_store = ReminderStore(str(db))
    first = NotificationOutbox(str(db))
    reminder_store.add("persistent notification", "2020-01-01T00:00:00Z")
    first.enqueue_due(reminder_store)

    second = NotificationOutbox(str(db))
    assert second.list()[0]["message"] == "persistent notification"
