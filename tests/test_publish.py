"""Canal de publicación gratuita (§9.4): solo entrega imágenes ya aprobadas."""
import pytest

from fondoclaro.config import Blocked
from fondoclaro.serialization import read_json
from fondoclaro.workflow.publish import publish_site

from test_workflow_audit import registry, sealed  # noqa: F401  (fixtures compartidas)


def test_nothing_published_without_approval(registry, sealed):  # noqa: F811
    with pytest.raises(Blocked, match="NOTHING_APPROVED"):
        publish_site(registry, "2026-10")
    assert not (registry.root/"site").exists()


def test_publishes_only_approved_fund(registry, sealed):  # noqa: F811
    registry.approve(sealed, sealed, without_external=True)
    folder, missing = publish_site(registry, "2026-10")
    assert missing == ["all", "A", "B", "D", "E"]
    assert (folder/"fondo_C.png").exists()
    assert not (folder/"fondo_A.png").exists()
    page = (folder/"index.html").read_text()
    assert "Fondo C" in page and "Intermedio" in page
    assert "Fondo A" not in page and "Fondo B" not in page


def test_page_caption_is_the_approved_text_only(registry, sealed):  # noqa: F811
    registry.approve(sealed, sealed, without_external=True)
    folder, _ = publish_site(registry, "2026-10")
    entry = read_json(registry.reports/"approved_index.json")["2026-10/C"]
    assert entry["whatsapp_text"] in (folder/"index.html").read_text()


def test_catalog_and_root_index(registry, sealed):  # noqa: F811
    registry.approve(sealed, sealed, without_external=True)
    publish_site(registry, "2026-10")
    site = registry.root/"site"
    catalog = read_json(site/"periods.json")
    assert catalog["periods"] == ["2026-10"] and catalog["latest"] == "2026-10"
    assert catalog["images"]["fondo_C"] == "2026-10/fondo_C.png"
    assert 'src="2026-10/fondo_C.png"' in (site/"index.html").read_text()
    assert (site/".nojekyll").exists()


def test_tampered_png_blocks_publication(registry, sealed):  # noqa: F811
    registry.approve(sealed, sealed, without_external=True)
    (registry.directory(sealed)/"infographic.png").write_bytes(b"modified")
    with pytest.raises(Blocked, match="CONTENT_CHANGED"):
        publish_site(registry, "2026-10")


def test_invalid_period_rejected(registry, sealed):  # noqa: F811
    registry.approve(sealed, sealed, without_external=True)
    with pytest.raises((Blocked, ValueError)):
        publish_site(registry, "2026-13")
