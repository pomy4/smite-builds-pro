import os
from pathlib import Path

import dotenv


class WebapiUpdaterLogManagerConfig:
    pass


class WebapiUpdaterConfig(WebapiUpdaterLogManagerConfig):
    def __init__(self) -> None:
        super().__init__()

        self.hmac_key_hex = get_required_env_var("HMAC_KEY_HEX")


class WebapiConfig(WebapiUpdaterConfig):
    def __init__(self) -> None:
        super().__init__()

        self.smite_dev_id = get_required_env_var("SMITE_DEV_ID")
        self.smite_auth_key = get_required_env_var("SMITE_AUTH_KEY")


class UpdaterConfig(WebapiUpdaterConfig):
    def __init__(self) -> None:
        super().__init__()

        self.backend_url = get_required_env_var("BACKEND_URL")
        self.use_watchdog = os.environ.get("USE_WATCHDOG", "") == "1"
        self.matches_with_no_stats = set(
            os.environ.get("MATCHES_WITH_NO_STATS", "").split(",")
        )


class LogManagerConfig(WebapiUpdaterLogManagerConfig):
    def __init__(self) -> None:
        super().__init__()

        self.ntfy_topic = get_required_env_var("NTFY_TOPIC")


def get_required_env_var(key: str) -> str:
    if key not in os.environ:
        raise RuntimeError(f"Environment variable is unset: {key}")

    value = os.environ[key]
    if not value:
        raise RuntimeError(f"Environment variable is empty: {key}")

    return value


_config: None | WebapiUpdaterLogManagerConfig = None


def load_webapi_config() -> None:
    global _config
    load_dotenv()
    _config = WebapiConfig()


def load_updater_config() -> None:
    global _config
    load_dotenv()
    _config = UpdaterConfig()


def load_log_manager_config() -> None:
    global _config
    load_dotenv()
    _config = LogManagerConfig()


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


def get_log_manager_config() -> LogManagerConfig:
    if _config is None:
        raise RuntimeError("load_config was not called")

    if not isinstance(_config, LogManagerConfig):
        raise RuntimeError("Different load_config was called")

    return _config
