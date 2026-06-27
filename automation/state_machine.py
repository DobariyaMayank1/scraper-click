"""
State machine for the automation workflow.

Each automation cycle progresses through a sequence of states.
New states can be added by extending the AutomationState enum
and updating the TRANSITIONS map.
"""

from enum import Enum, auto


class AutomationState(Enum):
    """All possible states in the automation lifecycle."""
    IDLE = auto()
    OPEN_SOURCE = auto()
    WAIT_PAGE = auto()
    HANDLE_POPUP = auto()
    LOCATE_AD = auto()
    CLICK_AD = auto()
    WAIT_DESTINATION = auto()
    DESTINATION_READY = auto()
    RETURN_SOURCE = auto()
    WAIT_NEXT_CYCLE = auto()
    STOPPED = auto()
    ERROR = auto()


# Allowed transitions: state -> set of valid next states
TRANSITIONS = {
    AutomationState.IDLE: {
        AutomationState.OPEN_SOURCE,
        AutomationState.STOPPED,
    },
    AutomationState.OPEN_SOURCE: {
        AutomationState.WAIT_PAGE,
        AutomationState.ERROR,
        AutomationState.STOPPED,
    },
    AutomationState.WAIT_PAGE: {
        AutomationState.HANDLE_POPUP,
        AutomationState.ERROR,
        AutomationState.STOPPED,
    },
    AutomationState.HANDLE_POPUP: {
        AutomationState.LOCATE_AD,
        AutomationState.ERROR,
        AutomationState.STOPPED,
    },
    AutomationState.LOCATE_AD: {
        AutomationState.CLICK_AD,
        AutomationState.WAIT_NEXT_CYCLE,    # No ads found — skip to next cycle
        AutomationState.ERROR,
        AutomationState.STOPPED,
    },
    AutomationState.CLICK_AD: {
        AutomationState.WAIT_DESTINATION,
        AutomationState.LOCATE_AD,          # Click failed — retry another ad
        AutomationState.WAIT_NEXT_CYCLE,    # All retries exhausted
        AutomationState.ERROR,
        AutomationState.STOPPED,
    },
    AutomationState.WAIT_DESTINATION: {
        AutomationState.DESTINATION_READY,
        AutomationState.RETURN_SOURCE,      # Destination failed to load
        AutomationState.ERROR,
        AutomationState.STOPPED,
    },
    AutomationState.DESTINATION_READY: {
        AutomationState.RETURN_SOURCE,
        AutomationState.ERROR,
        AutomationState.STOPPED,
    },
    AutomationState.RETURN_SOURCE: {
        AutomationState.WAIT_NEXT_CYCLE,
        AutomationState.ERROR,
        AutomationState.STOPPED,
    },
    AutomationState.WAIT_NEXT_CYCLE: {
        AutomationState.OPEN_SOURCE,
        AutomationState.STOPPED,
    },
    AutomationState.ERROR: {
        AutomationState.OPEN_SOURCE,        # Recover by restarting cycle
        AutomationState.WAIT_NEXT_CYCLE,    # Or wait and retry
        AutomationState.STOPPED,
    },
    AutomationState.STOPPED: {
        AutomationState.IDLE,               # Can be restarted
    },
}


class StateMachine:
    """
    Manages automation state transitions with validation.

    Usage:
        sm = StateMachine()
        sm.transition(AutomationState.OPEN_SOURCE)
    """

    def __init__(self):
        self._state = AutomationState.IDLE

    @property
    def current_state(self):
        """Return the current automation state."""
        return self._state

    @property
    def state_name(self):
        """Return human-readable state name."""
        return self._state.name

    def transition(self, new_state):
        """
        Transition to a new state.

        Args:
            new_state: The target AutomationState.

        Returns:
            True if transition was valid, False otherwise.
        """
        valid_transitions = TRANSITIONS.get(self._state, set())

        if new_state not in valid_transitions:
            # Log but don't crash — always allow STOPPED as an escape hatch
            if new_state == AutomationState.STOPPED:
                self._state = new_state
                return True
            return False

        self._state = new_state
        return True

    def reset(self):
        """Reset to IDLE state."""
        self._state = AutomationState.IDLE

    def is_running(self):
        """Return True if automation is actively processing (not idle/stopped)."""
        return self._state not in (
            AutomationState.IDLE,
            AutomationState.STOPPED,
        )
