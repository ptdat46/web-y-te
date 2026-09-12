from rest_framework.throttling import AnonRateThrottle


class AuthSensitiveThrottle(AnonRateThrottle):
    scope = 'auth_sensitive'


class VerificationThrottle(AnonRateThrottle):
    scope = 'verification'
