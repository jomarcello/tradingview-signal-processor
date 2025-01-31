class SecurityConfig:
    ENCRYPTION_ALGORITHM = 'AES-256-GCM'
    JWT_EXPIRY = 3600  # 1 hour
    REQUIRED_HEADERS = {
        'X-API-Key': str,
        'X-Client-ID': str
    }
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        return api_key_validator.validate(api_key)
