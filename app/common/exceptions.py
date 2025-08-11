class MissingAccessTokenError(RuntimeError):
    def __init__(self, provider: str, hint: str = ""):
        msg = f"No access token for provider={provider}."
        if hint:
            msg += f" {hint}"
        super().__init__(msg)

class TokenLoadError(RuntimeError):
    pass

class TokenRefreshError(RuntimeError):
    pass
