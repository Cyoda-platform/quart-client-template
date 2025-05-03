
class ChatNotFoundException(Exception):
    def __init__(self, message="Chat not found"):
        self.message = message
        self.status_code = 404
        super().__init__(self.message)

class UnauthorizedAccessException(Exception):
    def __init__(self, message="Unauthorized access"):
        self.message = message
        self.status_code = 401
        super().__init__(self.message)

class ForbiddenAccessException(Exception):
    def __init__(self, message="Forbidden access"):
        self.message = message
        self.status_code = 403
        super().__init__(self.message)