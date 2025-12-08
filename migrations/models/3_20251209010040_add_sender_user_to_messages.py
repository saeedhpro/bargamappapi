from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "chat_messages" ADD "sender_user_id" INT;
        ALTER TABLE "chat_messages" ADD CONSTRAINT "fk_chat_mes_user_c294e791" FOREIGN KEY ("sender_user_id") REFERENCES "user" ("id") ON DELETE SET NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "chat_messages" DROP CONSTRAINT IF EXISTS "fk_chat_mes_user_c294e791";
        ALTER TABLE "chat_messages" DROP COLUMN "sender_user_id";"""


MODELS_STATE = (
    "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"
    "54efofDr9ZaQ=="
)
