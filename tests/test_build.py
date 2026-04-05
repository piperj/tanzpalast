"""Unit tests for src/build.py — YAML → JSON compilation."""

import json
import sys
import textwrap
from pathlib import Path

import pytest

# Make src/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import build  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_yaml(tmp_path, content: str) -> Path:
    p = tmp_path / "tanzpalast.yaml"
    p.write_text(textwrap.dedent(content))
    return p


def run_build(tmp_path, yaml_content: str) -> list:
    """Write a temp YAML, monkey-patch build paths, run build(), return parsed JSON."""
    yaml_path = _make_yaml(tmp_path, yaml_content)
    data_dir = tmp_path / "data"
    json_path = data_dir / "tanzpalast-data.json"

    # Patch module-level paths
    original_yaml = build.YAML_PATH
    original_data = build.DATA_DIR
    original_json = build.JSON_PATH
    build.YAML_PATH = yaml_path
    build.DATA_DIR = data_dir
    build.JSON_PATH = json_path
    try:
        build.build()
    finally:
        build.YAML_PATH = original_yaml
        build.DATA_DIR = original_data
        build.JSON_PATH = original_json

    return json.loads(json_path.read_text())


# ---------------------------------------------------------------------------
# _video_dict tests
# ---------------------------------------------------------------------------

class TestVideoDict:
    def test_required_fields(self):
        raw = {"title": "Waltz Basics", "url": "https://youtu.be/abc"}
        result = build._video_dict(raw, 7)
        assert result["id"] == 7
        assert result["title"] == "Waltz Basics"
        assert result["url"] == "https://youtu.be/abc"

    def test_default_type_is_video(self):
        raw = {"title": "T", "url": "https://youtu.be/x"}
        assert build._video_dict(raw, 1)["type"] == "video"

    def test_explicit_type_pdf(self):
        raw = {"title": "T", "url": "https://example.com/sheet.pdf", "type": "pdf"}
        assert build._video_dict(raw, 1)["type"] == "pdf"

    def test_explicit_type_image(self):
        raw = {"title": "T", "url": "https://example.com/img.png", "type": "image"}
        assert build._video_dict(raw, 1)["type"] == "image"

    def test_default_tags_empty_list(self):
        raw = {"title": "T", "url": "https://youtu.be/x"}
        assert build._video_dict(raw, 1)["tags"] == []

    def test_tags_preserved(self):
        raw = {"title": "T", "url": "https://youtu.be/x", "tags": ["standard", "footwork"]}
        assert build._video_dict(raw, 1)["tags"] == ["standard", "footwork"]

    def test_tags_none_becomes_empty_list(self):
        raw = {"title": "T", "url": "https://youtu.be/x", "tags": None}
        assert build._video_dict(raw, 1)["tags"] == []

    def test_default_description_empty_string(self):
        raw = {"title": "T", "url": "https://youtu.be/x"}
        assert build._video_dict(raw, 1)["description"] == ""

    def test_description_preserved(self):
        raw = {"title": "T", "url": "https://youtu.be/x", "description": "Teacher: Anna"}
        assert build._video_dict(raw, 1)["description"] == "Teacher: Anna"

    def test_description_none_becomes_empty_string(self):
        raw = {"title": "T", "url": "https://youtu.be/x", "description": None}
        assert build._video_dict(raw, 1)["description"] == ""


# ---------------------------------------------------------------------------
# build() — happy path
# ---------------------------------------------------------------------------

class TestBuildHappyPath:
    MINIMAL_YAML = """\
        - dance: Waltz
          featured:
            title: International Level 2
            url: https://youtu.be/waltz
            tags: [standard]
          videos:
            - title: Natural Turn
              url: https://youtu.be/waltz-nt
              tags: [standard, footwork]
    """

    def test_output_is_list(self, tmp_path):
        result = run_build(tmp_path, self.MINIMAL_YAML)
        assert isinstance(result, list)

    def test_dance_name(self, tmp_path):
        result = run_build(tmp_path, self.MINIMAL_YAML)
        assert result[0]["dance"] == "Waltz"

    def test_featured_present(self, tmp_path):
        result = run_build(tmp_path, self.MINIMAL_YAML)
        assert "featured" in result[0]

    def test_featured_id_is_1(self, tmp_path):
        result = run_build(tmp_path, self.MINIMAL_YAML)
        assert result[0]["featured"]["id"] == 1

    def test_sub_video_id_is_2(self, tmp_path):
        result = run_build(tmp_path, self.MINIMAL_YAML)
        assert result[0]["videos"][0]["id"] == 2

    def test_featured_fields(self, tmp_path):
        result = run_build(tmp_path, self.MINIMAL_YAML)
        f = result[0]["featured"]
        assert f["title"] == "International Level 2"
        assert f["url"] == "https://youtu.be/waltz"
        assert f["type"] == "video"
        assert f["tags"] == ["standard"]

    def test_sub_video_fields(self, tmp_path):
        result = run_build(tmp_path, self.MINIMAL_YAML)
        v = result[0]["videos"][0]
        assert v["title"] == "Natural Turn"
        assert v["tags"] == ["standard", "footwork"]

    def test_empty_videos_list(self, tmp_path):
        yaml = """\
            - dance: Tango
              featured:
                title: Basic Tango
                url: https://youtu.be/tango
        """
        result = run_build(tmp_path, yaml)
        assert result[0]["videos"] == []

    def test_json_file_is_created(self, tmp_path):
        _make_yaml(tmp_path, self.MINIMAL_YAML)
        data_dir = tmp_path / "data"
        json_path = data_dir / "tanzpalast-data.json"
        build_original = (build.YAML_PATH, build.DATA_DIR, build.JSON_PATH)
        build.YAML_PATH = tmp_path / "tanzpalast.yaml"
        build.DATA_DIR = data_dir
        build.JSON_PATH = json_path
        build.build()
        build.YAML_PATH, build.DATA_DIR, build.JSON_PATH = build_original
        assert json_path.exists()

    def test_json_ends_with_newline(self, tmp_path):
        _make_yaml(tmp_path, self.MINIMAL_YAML)
        data_dir = tmp_path / "data"
        json_path = data_dir / "tanzpalast-data.json"
        build_original = (build.YAML_PATH, build.DATA_DIR, build.JSON_PATH)
        build.YAML_PATH = tmp_path / "tanzpalast.yaml"
        build.DATA_DIR = data_dir
        build.JSON_PATH = json_path
        build.build()
        build.YAML_PATH, build.DATA_DIR, build.JSON_PATH = build_original
        assert json_path.read_text().endswith("\n")


# ---------------------------------------------------------------------------
# build() — multiple dances, ID sequencing
# ---------------------------------------------------------------------------

class TestIdSequencing:
    MULTI_YAML = """\
        - dance: Waltz
          featured:
            title: Waltz Featured
            url: https://youtu.be/wf
          videos:
            - title: Waltz Sub 1
              url: https://youtu.be/ws1
            - title: Waltz Sub 2
              url: https://youtu.be/ws2
        - dance: Tango
          featured:
            title: Tango Featured
            url: https://youtu.be/tf
          videos:
            - title: Tango Sub 1
              url: https://youtu.be/ts1
    """

    def test_ids_are_globally_unique(self, tmp_path):
        result = run_build(tmp_path, self.MULTI_YAML)
        all_ids = [result[0]["featured"]["id"]]
        all_ids += [v["id"] for v in result[0]["videos"]]
        all_ids += [result[1]["featured"]["id"]]
        all_ids += [v["id"] for v in result[1]["videos"]]
        assert len(all_ids) == len(set(all_ids))

    def test_ids_are_sequential_from_1(self, tmp_path):
        result = run_build(tmp_path, self.MULTI_YAML)
        all_ids = [result[0]["featured"]["id"]]
        all_ids += [v["id"] for v in result[0]["videos"]]
        all_ids += [result[1]["featured"]["id"]]
        all_ids += [v["id"] for v in result[1]["videos"]]
        assert sorted(all_ids) == list(range(1, len(all_ids) + 1))

    def test_correct_dance_count(self, tmp_path):
        result = run_build(tmp_path, self.MULTI_YAML)
        assert len(result) == 2

    def test_dance_order_preserved(self, tmp_path):
        result = run_build(tmp_path, self.MULTI_YAML)
        assert result[0]["dance"] == "Waltz"
        assert result[1]["dance"] == "Tango"


# ---------------------------------------------------------------------------
# build() — error cases
# ---------------------------------------------------------------------------

class TestBuildErrors:
    def test_missing_dance_field_exits(self, tmp_path):
        yaml = """\
            - featured:
                title: No Dance Name
                url: https://youtu.be/x
        """
        with pytest.raises(SystemExit):
            run_build(tmp_path, yaml)

    def test_empty_dance_name_exits(self, tmp_path):
        yaml = """\
            - dance: ""
              featured:
                title: T
                url: https://youtu.be/x
        """
        with pytest.raises(SystemExit):
            run_build(tmp_path, yaml)

    def test_missing_featured_exits(self, tmp_path):
        yaml = """\
            - dance: Waltz
              videos:
                - title: T
                  url: https://youtu.be/x
        """
        with pytest.raises(SystemExit):
            run_build(tmp_path, yaml)

    def test_non_list_yaml_exits(self, tmp_path):
        yaml = "dance: Waltz\n"
        with pytest.raises(SystemExit):
            run_build(tmp_path, yaml)


# ---------------------------------------------------------------------------
# build() — real data smoke test
# ---------------------------------------------------------------------------

class TestRealData:
    """Smoke-test against the actual tanzpalast.yaml in the repo."""

    def test_real_yaml_builds_without_error(self):
        """build() against the real YAML must not raise or exit."""
        import importlib
        import io
        from contextlib import redirect_stdout
        # Re-import with default paths pointing at the real files
        importlib.reload(build)
        out = io.StringIO()
        with redirect_stdout(out):
            build.build()
        assert "Wrote" in out.getvalue()

    def test_real_output_has_required_fields(self):
        """Every dance entry in real output must have dance, featured, and videos."""
        import importlib
        importlib.reload(build)
        data = json.loads(build.JSON_PATH.read_text())
        for entry in data:
            assert "dance" in entry
            assert "featured" in entry
            assert "videos" in entry

    def test_real_output_all_ids_unique(self):
        """IDs across real output must all be unique integers."""
        import importlib
        importlib.reload(build)
        data = json.loads(build.JSON_PATH.read_text())
        ids = []
        for entry in data:
            ids.append(entry["featured"]["id"])
            ids.extend(v["id"] for v in entry["videos"])
        assert len(ids) == len(set(ids))

    def test_real_output_all_videos_have_type(self):
        """Every video entry (featured + sub) must have a valid type field."""
        import importlib
        importlib.reload(build)
        data = json.loads(build.JSON_PATH.read_text())
        valid_types = {"video", "pdf", "image"}
        for entry in data:
            assert entry["featured"]["type"] in valid_types
            for v in entry["videos"]:
                assert v["type"] in valid_types
