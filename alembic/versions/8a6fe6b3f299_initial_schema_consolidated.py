"""Preserva os dados apos a cadeia historica de migracoes.

A revisao antiga removia users durante upgrade. Ela agora e uma revisao
sem alteracoes de schema e conserva seu identificador para bancos existentes.
"""
revision = "8a6fe6b3f299"
down_revision = "b5edc4fe6d9a"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
