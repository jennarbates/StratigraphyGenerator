import pytest


from app import app


THREE_IMPORT_MAP = """<script type="importmap">
{
  "imports": {
    "three": "/static/vendor/three/three.module.min.js",
    "three/addons/": "/static/vendor/three/addons/"
  }
}
</script>"""
THREE_STATIC_PATHS = (
    "/static/vendor/three/three.module.min.js",
    "/static/vendor/three/three.core.min.js",
    "/static/vendor/three/addons/controls/OrbitControls.js",
    "/static/vendor/three/addons/loaders/OBJLoader.js",
    "/static/vendor/three/LICENSE",
    "/static/vendor/three/VERSION",
)
FORBIDDEN_THREE_SOURCES = (
    "unpkg",
    "jsdelivr",
    "esm.sh",
    "threejs.org/build",
)


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_visualizer_import_map_is_local_and_precedes_module_entry(client):
    response = client.get("/visualizer")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert THREE_IMPORT_MAP in html
    assert html.index(THREE_IMPORT_MAP) < html.index(
        '<script type="module" src="/static/visualizer/index.js"></script>'
    )


@pytest.mark.parametrize("static_path", THREE_STATIC_PATHS)
def test_three_vendor_files_are_served(client, static_path):
    response = client.get(static_path)

    assert response.status_code == 200
    assert response.data


def test_three_version_is_exactly_pinned(client):
    response = client.get("/static/vendor/three/VERSION")

    assert response.get_data(as_text=True) == "0.185.1\n"


def test_vendored_three_license_identifies_mit_license(client):
    response = client.get("/static/vendor/three/LICENSE")
    license_text = response.get_data(as_text=True)

    assert "The MIT License" in license_text
    assert "Copyright" in license_text
    assert "three.js authors" in license_text


@pytest.mark.parametrize(
    "static_path",
    (
        "/visualizer",
        "/static/visualizer/index.js",
        "/static/viewer3d.js",
    ),
)
def test_visualizer_sources_do_not_reference_external_three_hosts(
    client,
    static_path,
):
    response = client.get(static_path)
    source = response.get_data(as_text=True).lower()

    assert response.status_code == 200
    assert not any(host in source for host in FORBIDDEN_THREE_SOURCES)
    assert 'from "http://' not in source
    assert "from 'http://" not in source
    assert 'from "https://' not in source
    assert "from 'https://" not in source


@pytest.mark.parametrize(
    "static_path",
    (
        "/static/vendor/three/addons/controls/OrbitControls.js",
        "/static/vendor/three/addons/loaders/OBJLoader.js",
    ),
)
def test_three_addons_import_bare_three_specifier(client, static_path):
    response = client.get(static_path)
    source = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "from 'three';" in source or 'from "three";' in source
