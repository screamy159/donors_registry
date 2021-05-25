"""Přidáni ignorovaní dárci

Revision ID: 971ddb205e0c
Revises: 6fe71f4f1aba
Create Date: 2021-05-25 08:45:35.992441

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "971ddb205e0c"
down_revision = "6fe71f4f1aba"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "ignored_donors",
        sa.Column("rodne_cislo", sa.String(length=10), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("ignored_since", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("rodne_cislo"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("ignored_donors")
    # ### end Alembic commands ###
