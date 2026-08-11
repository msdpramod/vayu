from enum import Enum

class Risk(str, Enum):
    SAFE = "safe"
    CONFIRM = "confirm"
    BLOCKED = "blocked"

BLOCKED_TERMS = {
    "rm -rf", "format disk", "wipe disk", "delete all files", "password", "credential",
    "transfer money", "send money", "disable security", "unlock account"
}

CONFIRM_TERMS = {"shutdown", "reboot", "restart computer", "close all apps"}

def classify(command: str) -> Risk:
    text = command.lower()
    if any(term in text for term in BLOCKED_TERMS):
        return Risk.BLOCKED
    if any(term in text for term in CONFIRM_TERMS):
        return Risk.CONFIRM
    return Risk.SAFE
