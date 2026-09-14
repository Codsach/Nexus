from fastapi import Request
from fastapi.responses import JSONResponse


class NexusException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class TicketNotFound(NexusException):
    def __init__(self, ticket_id: str):
        super().__init__(f"Ticket '{ticket_id}' not found", 404)


class AgentError(NexusException):
    def __init__(self, agent: str, reason: str):
        super().__init__(f"Agent '{agent}' error: {reason}", 500)


async def nexus_exception_handler(request: Request, exc: NexusException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "type": type(exc).__name__},
    )
