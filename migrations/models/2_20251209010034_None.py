from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "subscription_plans" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(100) NOT NULL,
    "description" TEXT,
    "price" INT NOT NULL DEFAULT 0,
    "duration_days" INT,
    "daily_plant_id_limit" INT NOT NULL DEFAULT 1,
    "daily_disease_id_limit" INT NOT NULL DEFAULT 1,
    "is_default" BOOL NOT NULL DEFAULT False,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "roles" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(50) NOT NULL UNIQUE,
    "display_name" VARCHAR(100) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "is_active" BOOL NOT NULL DEFAULT True
);
CREATE TABLE IF NOT EXISTS "user" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "phone" VARCHAR(20) NOT NULL UNIQUE,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "is_active" BOOL NOT NULL DEFAULT True,
    "role_id" INT DEFAULT 1 REFERENCES "roles" ("id") ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS "usage_logs" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "tool_type" VARCHAR(10) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "usage_logs"."tool_type" IS 'PLANT_ID: plant_id\nDISEASE_ID: disease_id';
CREATE TABLE IF NOT EXISTS "user_subscriptions" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "frozen_daily_plant_id_limit" INT NOT NULL,
    "frozen_daily_disease_id_limit" INT NOT NULL,
    "start_date" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "end_date" TIMESTAMPTZ,
    "is_active" BOOL NOT NULL DEFAULT True,
    "plan_id" INT REFERENCES "subscription_plans" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "plant_histories" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "image_path" VARCHAR(500),
    "image_paths" JSONB,
    "plant_name" VARCHAR(255) NOT NULL,
    "common_name" VARCHAR(255),
    "accuracy" DOUBLE PRECISION NOT NULL,
    "description" TEXT,
    "details" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "user_garden" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "plant_name" VARCHAR(255) NOT NULL,
    "nickname" VARCHAR(255),
    "image_path" VARCHAR(500) NOT NULL,
    "image_paths" JSONB,
    "details" JSONB NOT NULL,
    "origin_history_id" INT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "chat_conversations" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "last_activity" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "chat_conversations"."user_id" IS 'کاربری که این مکالمه را ایجاد کرده';
CREATE TABLE IF NOT EXISTS "chat_messages" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "sender" VARCHAR(20) NOT NULL,
    "text" TEXT,
    "file_url" VARCHAR(400),
    "message_type" VARCHAR(20) NOT NULL DEFAULT 'text',
    "is_delivered" BOOL NOT NULL DEFAULT False,
    "is_seen" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "conversation_id" INT NOT NULL REFERENCES "chat_conversations" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "l6f/AXO2Ka8="
)
