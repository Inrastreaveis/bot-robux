"""Backup consistente do SQLite e transcrições para um repositório PRIVADO no GitHub."""
import asyncio
import base64
import io
import json
import logging
import os
from pathlib import Path
import sqlite3
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone

from database.database import DATABASE

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
PERIOD_SECONDS = 600  # 10 minutos
MAX_FILE_BYTES = 20 * 1024 * 1024


def _http_json(url, token, method="GET", payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "robux-store-backup",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.load(resp)


def _make_archive():
    """Usa a API de backup do SQLite, segura mesmo com escritas concorrentes."""
    if not DATABASE.is_file():
        raise FileNotFoundError(f"Banco não encontrado: {DATABASE}")
    data = io.BytesIO()
    with tempfile.TemporaryDirectory() as folder:
        snapshot_path = Path(folder) / "database.db"
        with sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True, timeout=30) as source:
            with sqlite3.connect(str(snapshot_path), timeout=30) as destination:
                source.backup(destination)
        with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(snapshot_path, "database.db")
            bundle.writestr("backup_info.json", json.dumps({
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "contents": "Banco SQLite e transcrições HTML, quando disponíveis",
            }, ensure_ascii=False))
            for directory in (ROOT / "transcripts", ROOT / "utils" / "transcripts"):
                if not directory.is_dir():
                    continue
                for file in directory.glob("*.html"):
                    if file.is_file() and file.stat().st_size <= MAX_FILE_BYTES:
                        bundle.write(file, file.relative_to(ROOT).as_posix())
    result = data.getvalue()
    if len(result) > MAX_FILE_BYTES:
        raise ValueError("Backup superior a 20 MB. Usar armazenamento de backup próprio.")
    return result


def _backup_once(token, repository, branch):
    api_base = f"https://api.github.com/repos/{repository}/contents"
    remote_path = "backups/ultimo-backup.zip"
    url = f"{api_base}/{remote_path}?ref={urllib.parse.quote(branch, safe='')}"
    sha = None
    try:
        current = _http_json(url, token)
        sha = current.get("sha")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    archive = _make_archive()
    payload = {
        "message": f"Backup automático {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        "content": base64.b64encode(archive).decode("ascii"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    upload_url = f"{api_base}/{remote_path}"
    _http_json(upload_url, token, method="PUT", payload=payload)
    logger.info("Backup do SQLite enviado com sucesso ao GitHub.")


async def github_backup_loop(bot):
    token = os.getenv("GITHUB_BACKUP_TOKEN", "").strip()
    repository = os.getenv("GITHUB_BACKUP_REPO", "").strip()
    branch = os.getenv("GITHUB_BACKUP_BRANCH", "main").strip()
    if not token or not repository:
        logger.warning("Backup GitHub desligado: defina GITHUB_BACKUP_TOKEN e GITHUB_BACKUP_REPO.")
        return
    if repository.count("/") != 1 or not all(repository.split("/")):
        logger.error("GITHUB_BACKUP_REPO inválido: esperado usuario/repositorio")
        return
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            # Falhar de forma segura: nunca escreve credenciais nem dados em logs.
            await asyncio.to_thread(_backup_once, token, repository, branch)
        except Exception as error:
            logger.error("Falha no backup GitHub: %s: %s", type(error).__name__, error)
        await asyncio.sleep(PERIOD_SECONDS)
