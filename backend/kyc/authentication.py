from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import Account


class SimpleTokenAuthentication(BaseAuthentication):
    keyword = "Token"

    def authenticate(self, request):
        token = self._get_token(request)
        if not token:
            return None

        try:
            account = Account.objects.get(token=token)
        except Account.DoesNotExist as exc:
            raise AuthenticationFailed("Invalid API token.") from exc
        return (account, None)

    def _get_token(self, request):
        header = get_authorization_header(request).decode("utf-8")
        if header:
            parts = header.split()
            if len(parts) == 2 and parts[0].lower() == self.keyword.lower():
                return parts[1].strip()
            raise AuthenticationFailed("Use `Authorization: Token <token>`.")
        return request.headers.get("X-API-Token")

