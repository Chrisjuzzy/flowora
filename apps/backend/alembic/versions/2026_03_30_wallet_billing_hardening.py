"""wallet_billing_hardening

Revision ID: 2026_03_30_wallet_billing_hardening
Revises: 2026_03_02_marketplace_agents
Create Date: 2026-03-30 10:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "2026_03_30_wallet_billing_hardening"
down_revision = "2026_03_02_marketplace_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.execute("UPDATE wallets SET balance = 0 WHERE balance IS NULL")

    if dialect == "postgresql":
        op.execute(
            """
            INSERT INTO transactions (
                wallet_id,
                amount,
                type,
                description,
                reference_id,
                created_at,
                tenant_id
            )
            SELECT
                w.id,
                ABS(w.balance)::numeric(18, 6),
                'system_correction',
                'Negative wallet balance reset to zero during billing hardening',
                CONCAT('wallet-reset-', w.id, '-', EXTRACT(EPOCH FROM NOW())::bigint),
                NOW(),
                w.tenant_id
            FROM wallets w
            WHERE w.balance < 0
            """
        )

        op.execute("UPDATE wallets SET balance = 0, updated_at = NOW() WHERE balance < 0")

        op.execute(
            """
            ALTER TABLE wallets
            ALTER COLUMN balance TYPE numeric(18, 6)
            USING ROUND(COALESCE(balance, 0)::numeric, 6)
            """
        )
        op.execute(
            """
            ALTER TABLE transactions
            ALTER COLUMN amount TYPE numeric(18, 6)
            USING ROUND(COALESCE(amount, 0)::numeric, 6)
            """
        )
        op.execute(
            """
            ALTER TABLE wallet_charges
            ALTER COLUMN amount TYPE numeric(18, 6)
            USING ROUND(COALESCE(amount, 0)::numeric, 6)
            """
        )
        op.execute(
            """
            ALTER TABLE invoices
            ALTER COLUMN amount TYPE numeric(18, 6)
            USING ROUND(COALESCE(amount, 0)::numeric, 6)
            """
        )
        op.execute(
            """
            ALTER TABLE marketplace_listings
            ALTER COLUMN price TYPE numeric(18, 6)
            USING CASE
                WHEN price IS NULL THEN NULL
                ELSE ROUND(price::numeric, 6)
            END
            """
        )
        op.execute(
            """
            ALTER TABLE purchases
            ALTER COLUMN amount TYPE numeric(18, 6)
            USING ROUND(COALESCE(amount, 0)::numeric, 6)
            """
        )
        op.execute(
            """
            ALTER TABLE purchases
            ALTER COLUMN commission TYPE numeric(18, 6)
            USING ROUND(COALESCE(commission, 0)::numeric, 6)
            """
        )
        op.execute(
            """
            ALTER TABLE purchases
            ALTER COLUMN seller_revenue TYPE numeric(18, 6)
            USING ROUND(COALESCE(seller_revenue, 0)::numeric, 6)
            """
        )
        op.execute("ALTER TABLE wallets ALTER COLUMN balance SET DEFAULT 0")
        op.execute("ALTER TABLE wallets ALTER COLUMN balance SET NOT NULL")
        op.execute("ALTER TABLE wallets DROP CONSTRAINT IF EXISTS ck_wallets_balance_non_negative")
        op.execute(
            """
            ALTER TABLE wallets
            ADD CONSTRAINT ck_wallets_balance_non_negative
            CHECK (balance >= 0)
            """
        )
        return

    op.execute("UPDATE wallets SET balance = 0, updated_at = CURRENT_TIMESTAMP WHERE balance < 0")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE wallets DROP CONSTRAINT IF EXISTS ck_wallets_balance_non_negative")
        op.execute(
            """
            ALTER TABLE purchases
            ALTER COLUMN seller_revenue TYPE double precision
            USING seller_revenue::double precision
            """
        )
        op.execute(
            """
            ALTER TABLE purchases
            ALTER COLUMN commission TYPE double precision
            USING commission::double precision
            """
        )
        op.execute(
            """
            ALTER TABLE purchases
            ALTER COLUMN amount TYPE double precision
            USING amount::double precision
            """
        )
        op.execute(
            """
            ALTER TABLE marketplace_listings
            ALTER COLUMN price TYPE double precision
            USING price::double precision
            """
        )
        op.execute(
            """
            ALTER TABLE invoices
            ALTER COLUMN amount TYPE double precision
            USING amount::double precision
            """
        )
        op.execute(
            """
            ALTER TABLE wallet_charges
            ALTER COLUMN amount TYPE double precision
            USING amount::double precision
            """
        )
        op.execute(
            """
            ALTER TABLE transactions
            ALTER COLUMN amount TYPE double precision
            USING amount::double precision
            """
        )
        op.execute(
            """
            ALTER TABLE wallets
            ALTER COLUMN balance TYPE double precision
            USING balance::double precision
            """
        )
        op.execute("ALTER TABLE wallets ALTER COLUMN balance DROP NOT NULL")
        op.execute("ALTER TABLE wallets ALTER COLUMN balance DROP DEFAULT")
