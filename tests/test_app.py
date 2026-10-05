from app import create_app
from config import DEFAULT_PORT, load_config


def test_config_defaults():
    config = load_config({})
    assert config["PORT"] == DEFAULT_PORT
    assert config["DATABASE"].name == "playlist_battle.db"


def test_config_reads_env_vars(tmp_path):
    config = load_config({"PORT": "9123", "DATA_DIR": str(tmp_path)})
    assert config["PORT"] == 9123
    assert config["DATABASE"] == tmp_path / "playlist_battle.db"


def test_create_app_makes_data_dir(tmp_path):
    data_dir = tmp_path / "nested" / "data"
    create_app({"DATA_DIR": str(data_dir)})
    assert data_dir.is_dir()


def test_health_endpoint(tmp_path):
    client = create_app({"DATA_DIR": str(tmp_path)}).test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
