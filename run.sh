#!/bin/bash
# https://github.com/adriancooney/Taskfile

function dev {
    # runs backend.webapi.__main__
    # PYTHONPATH because bottle reloader doesn't support -m
    PYTHONPATH="." python backend/webapi "$@"
}

function start {
    gunicorn --bind 127.0.0.1:4000 backend.webapi.gunicorn:application
}

function start_docker {
    python -m backend.webapi.tools.create_db || return
    python -m backend.webapi.tools.migrate_db || return
    exec gunicorn --bind 0.0.0.0:4000 backend.webapi.gunicorn:application
}

function updater {
    python -m backend.updater.updater
}

function log_manager {
    python -m backend.log_manager.log_manager
}

function item_viewer {
    python -m backend.item_viewer.item_viewer "$@"
}

function lint {
    black . --check || return
    isort . --check-only || return
    flake8 . || return
    mypy . || return
    (cd frontend && npm run format-check) || return
    (cd frontend && npm run lint-check)
}

function test {
    # Without 'python -m' fails, probably due to no __init__.py files.
    python -m pytest backend
}

function build {
    (cd frontend && npm run build) || return
}

function deploy {
    lint || return
    test || return
    build || return
    vps_deploy.sh code static
}

function options {
    # Prints all functions in the file.
    compgen -A function
}

"${@-options}"