"""Compatibilidad: reexporta customer_drive_config (Drive es por customer, no por school)."""

from app.backend.utils.customer_drive_config import (  # noqa: F401
    GOOGLE_DRIVE_DISABLED_MESSAGE,
    GOOGLE_DRIVE_ENABLED,
    CredKind,
    DriveCustomerConfig,
    DriveSchoolConfig,  # alias de DriveCustomerConfig
    assert_google_drive_enabled,
    customer_drive_configured,
    drive_configured,
    load_agents_global_drive_config,
    load_customer_drive_config,
    load_drive_config,
    parse_drive_credentials_json,
    test_drive_connection,
    _parse_service_account_json,
    _service_account_info_from_env_file,
)
