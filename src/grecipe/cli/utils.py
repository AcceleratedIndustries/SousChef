"""Shared CLI utilities."""

from grecipe.models.chat import log_chat


def _maybe_log(conn, user_msg, assistant_msg, action_type, entity_type, entity_id=None):
    """Log a chat entry if messages are provided."""
    if user_msg is not None or assistant_msg is not None:
        log_chat(
            conn,
            user_message=user_msg,
            assistant_response=assistant_msg,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
        )
