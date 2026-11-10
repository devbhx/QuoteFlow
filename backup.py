"""Cópias consistentes do banco SQLite, sem modificar os registros originais."""

from contextlib import closing
from datetime import datetime
import os
from pathlib import Path
import sqlite3
import tempfile


PASTA_BACKUPS = Path(__file__).resolve().parent / "backups"


def criar_backup(conexao, pasta=PASTA_BACKUPS):
    """Copia dados confirmados e publica um arquivo novo somente após validá-lo."""
    if conexao.in_transaction:
        raise ValueError("Finalize a transação pendente antes de criar o backup.")
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    descritor, nome_temporario = tempfile.mkstemp(prefix=".quoteflow_", suffix=".tmp", dir=pasta)
    os.close(descritor)
    temporario = Path(nome_temporario)
    try:
        with closing(sqlite3.connect(temporario)) as destino:
            conexao.backup(destino)
            integridade = destino.execute("PRAGMA integrity_check").fetchall()
            if integridade != [("ok",)]:
                raise ValueError("A cópia não passou na verificação de integridade.")
            if destino.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("A cópia contém vínculos inválidos entre registros.")
        base = f"quoteflow_{datetime.now().astimezone():%Y%m%d_%H%M%S}"
        numero = 0
        while True:
            caminho = pasta / f"{base}{'_' + str(numero) if numero else ''}.db"
            try:
                # Cria o nome final sem sobrescrever; ambos ficam na mesma pasta.
                os.link(temporario, caminho)
            except FileExistsError:
                numero += 1
                continue
            return caminho
    finally:
        # Limpa somente o arquivo temporário criado por esta operação.
        temporario.unlink(missing_ok=True)
