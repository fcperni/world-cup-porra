"""Persistencia de ``results.json`` en el repositorio vía la API de GitHub.

En Streamlit Cloud el disco es efímero: para que los resultados sobrevivan a los
reinicios, commiteamos el JSON al repo usando un token personal (PAT) guardado en
``st.secrets``. En local (sin secrets) la app solo escribe en disco.

Configuración esperada en ``.streamlit/secrets.toml``::

    [github]
    token = "ghp_..."          # PAT con permiso 'contents' sobre el repo
    repo = "fcperni/world-cup-porra"
    path = "data/results.json"  # opcional (por defecto)
    branch = "main"             # opcional (por defecto)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CommitOutcome:
    ok: bool
    message: str


def commit_file(token: str, repo: str, path: str, content: str,
                branch: str = "main", commit_message: str = "Actualizar resultados") -> CommitOutcome:
    """Crea o actualiza ``path`` en ``repo`` con ``content``. Devuelve el resultado."""
    try:
        from github import Github, GithubException
    except ImportError:
        return CommitOutcome(False, "PyGithub no está instalado.")

    try:
        gh = Github(token)
        repository = gh.get_repo(repo)
        try:
            existing = repository.get_contents(path, ref=branch)
            if existing.decoded_content.decode("utf-8") == content:
                return CommitOutcome(True, "Sin cambios respecto al repositorio.")
            repository.update_file(path, commit_message, content, existing.sha, branch=branch)
        except GithubException as exc:
            if exc.status == 404:  # el archivo aún no existe
                repository.create_file(path, commit_message, content, branch=branch)
            else:
                raise
        return CommitOutcome(True, f"Guardado en {repo}@{branch}:{path}.")
    except Exception as exc:  # noqa: BLE001
        return CommitOutcome(False, f"No se pudo commitear: {exc}")
