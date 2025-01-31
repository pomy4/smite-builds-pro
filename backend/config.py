import ast
import os
from pathlib import Path

import dotenv


class BaseConfig:
    pass


class WebapiUpdaterConfig(BaseConfig):
    def __init__(self) -> None:
        super().__init__()

        self.hmac_key_hex = get_required_env_var("HMAC_KEY_HEX")


class WebapiConfig(WebapiUpdaterConfig):
    def __init__(self) -> None:
        super().__init__()

        self.smite_dev_id = get_required_env_var("SMITE_DEV_ID")
        self.smite_auth_key = get_required_env_var("SMITE_AUTH_KEY")
        # If needed, change to a config file.
        self.backup_item_names = ast.literal_eval(
            os.environ.get("BACKUP_ITEM_NAMES", "{}")
        )


class UpdaterConfig(WebapiUpdaterConfig):
    def __init__(self) -> None:
        super().__init__()

        self.backend_url = get_required_env_var("BACKEND_URL")
        self.matches_with_no_stats = set(
            os.environ.get("MATCHES_WITH_NO_STATS", "").split(",")
        )


def get_required_env_var(key: str) -> str:
    if key not in os.environ:
        raise RuntimeError(f"Environment variable is unset: {key}")

    value = os.environ[key]
    if not value:
        raise RuntimeError(f"Environment variable is empty: {key}")

    return value


_config: None | BaseConfig = None


def load_webapi_config() -> None:
    global _config
    load_dotenv()
    _config = WebapiConfig()


def load_updater_config() -> None:
    global _config
    load_dotenv()
    _config = UpdaterConfig()


def load_dotenv() -> None:
    dotenv.load_dotenv(get_project_root_dir() / ".env")


def get_project_root_dir() -> Path:
    path = Path(__file__)
    cd_up_cnt = __name__.count(".") + 1
    for _ in range(cd_up_cnt):
        path = path.parent
    return path


def get_webapi_config() -> WebapiConfig:
    if _config is None:
        raise RuntimeError("load_config was not called")

    if not isinstance(_config, WebapiConfig):
        raise RuntimeError("Different load_config was called")

    return _config


def get_updater_config() -> UpdaterConfig:
    if _config is None:
        raise RuntimeError("load_config was not called")

    if not isinstance(_config, UpdaterConfig):
        raise RuntimeError("Different load_config was called")

    return _config
