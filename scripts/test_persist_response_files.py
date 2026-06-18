"""Prueba unitaria de persistencia de archivos generados (sin llamar a OpenAI)."""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.backend.services.agent_response_files_service import (
    persist_code_interpreter_outputs,
    try_capture_from_container,
)


def test_persist_from_container_list_fallback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agent_id = "agent-test"
    container_id = "cntr_test"
    user_file_id = "file-user-1"
    generated_id = "file-gen-1"
    content = b"PK fake docx content"

    list_page = SimpleNamespace(
        data=[
            SimpleNamespace(
                id=user_file_id,
                source="user",
                path="/mnt/data/2 E ISABELLA DIAZ.docx",
                created_at=1,
            ),
            SimpleNamespace(
                id=generated_id,
                source="assistant",
                path="/mnt/data/Informe_Familia_Isabella_Diaz.docx",
                created_at=99,
            ),
        ]
    )

    mock_client = MagicMock()
    mock_client.containers.files.list.return_value = list_page
    mock_client.containers.files.content.retrieve.return_value = io.BytesIO(content)

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    response = SimpleNamespace(
        output_text="Archivo generado: Informe_Familia_Isabella_Diaz.docx",
        output=[],
    )

    with patch(
        "app.backend.services.openai_agent_service.get_openai_client",
        return_value=mock_client,
    ):
        saved = persist_code_interpreter_outputs(
            mock_db,
            agent_id,
            response,
            container_id,
            [user_file_id],
        )

    assert len(saved) == 1
    assert saved[0]["name"] == "Informe_Familia_Isabella_Diaz.docx"
    mock_client.containers.files.content.retrieve.assert_called_once()


def test_early_capture_uses_container_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agent_id = "agent-test"
    container_id = "cntr_test"
    generated_id = "file-gen-2"
    content = b"PK another docx"

    list_page = SimpleNamespace(
        data=[
            SimpleNamespace(
                id=generated_id,
                source="assistant",
                path="/mnt/data/Informe_Familia_Isabella_Diaz.docx",
                created_at=50,
            )
        ]
    )

    mock_client = MagicMock()
    mock_client.containers.files.list.return_value = list_page
    mock_client.containers.files.content.retrieve.return_value = io.BytesIO(content)
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    with patch(
        "app.backend.services.openai_agent_service.get_openai_client",
        return_value=mock_client,
    ):
        saved = try_capture_from_container(
            mock_db,
            agent_id,
            container_id,
            [],
        )

    assert len(saved) == 1
    assert "Informe_Familia" in saved[0]["name"]


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
