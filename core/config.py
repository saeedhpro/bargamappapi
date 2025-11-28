class Settings:
    JWT_SECRET = "SUPER_SECRET_64BIT_KEY"
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = 60
    PG_URL = "postgres://postgres:1234@localhost:5432/bargam"
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    OTP_EXPIRE_SECONDS = 120


settings = Settings()
