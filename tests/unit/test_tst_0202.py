"""TST-0202 – sdd vision show und sdd vision edit (Unit)
Spec: SPEC-0046 · Contract: CON-0176
"""
import subprocess
from unittest.mock import patch, MagicMock
import pytest


class TestVisionShow:
    def test_show_outputs_file_content(self, tmp_path, capsys):
        """INV-02: show gibt Inhalt aus, verändert Datei nicht."""
        from tool.sdd_cli.vision.show import VisionReader

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        vision_file = sdd_dir / "vision.md"
        vision_file.write_text("# Meine Vision\n\n## Vision\nToller Plan.\n")

        reader = VisionReader(sdd_dir=sdd_dir)
        reader.show()

        captured = capsys.readouterr()
        assert "Toller Plan." in captured.out
        assert vision_file.read_text() == "# Meine Vision\n\n## Vision\nToller Plan.\n"

    def test_show_raises_when_vision_missing(self, tmp_path):
        """INV-01: Fehlermeldung + Exception wenn vision.md fehlt."""
        from tool.sdd_cli.vision.show import VisionReader, VisionNotFoundError

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()

        with pytest.raises(VisionNotFoundError) as exc_info:
            VisionReader(sdd_dir=sdd_dir).show()

        assert "vision init" in str(exc_info.value).lower()

    def test_show_does_not_modify_file(self, tmp_path):
        """INV-02: Datei nach show byte-identisch."""
        from tool.sdd_cli.vision.show import VisionReader

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        vision_file = sdd_dir / "vision.md"
        original = "# Vision\n## Features\n"
        vision_file.write_text(original)

        VisionReader(sdd_dir=sdd_dir).show()

        assert vision_file.read_text() == original


class TestVisionEdit:
    def test_edit_opens_editor_from_env(self, tmp_path, monkeypatch):
        """INV-03: $EDITOR gesetzt → Editor mit vision.md-Pfad gestartet."""
        from tool.sdd_cli.vision.edit import VisionEditor

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        (sdd_dir / "vision.md").write_text("# Vision")
        monkeypatch.setenv("EDITOR", "myeditor")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            VisionEditor(sdd_dir=sdd_dir).open()

        called_args = mock_popen.call_args[0][0]
        assert "myeditor" in called_args
        assert str(sdd_dir / "vision.md") in called_args

    def test_edit_prints_path_when_no_editor(self, tmp_path, monkeypatch, capsys):
        """INV-03: $EDITOR nicht gesetzt → Pfad auf stdout, kein Fehler."""
        from tool.sdd_cli.vision.edit import VisionEditor

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        (sdd_dir / "vision.md").write_text("# Vision")
        monkeypatch.delenv("EDITOR", raising=False)

        VisionEditor(sdd_dir=sdd_dir).open()

        captured = capsys.readouterr()
        assert str(sdd_dir / "vision.md") in captured.out

    def test_edit_does_not_wait_for_editor(self, tmp_path, monkeypatch):
        """INV-04: open() wartet nicht auf Editor-Prozess (Popen, nicht run/call)."""
        from tool.sdd_cli.vision.edit import VisionEditor

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        (sdd_dir / "vision.md").write_text("# Vision")
        monkeypatch.setenv("EDITOR", "vim")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            VisionEditor(sdd_dir=sdd_dir).open()

        mock_popen.assert_called_once()
        mock_popen.return_value.wait.assert_not_called()

    def test_edit_raises_when_vision_missing(self, tmp_path, monkeypatch):
        """INV-01: Exception wenn vision.md fehlt."""
        from tool.sdd_cli.vision.edit import VisionEditor, VisionNotFoundError

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        monkeypatch.setenv("EDITOR", "vim")

        with pytest.raises(VisionNotFoundError):
            VisionEditor(sdd_dir=sdd_dir).open()
