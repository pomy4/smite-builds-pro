#!/bin/bash
# https://github.com/adriancooney/Taskfile

function dev {
    # runs backend.webapi.__main__
    # PYTHONPATH because bottle reloader doesn't support -m
    PYTHONPATH="." python backend/webapi "$@"
}

function start {
    gunicorn --bind 127.0.0.1:4000 backend.webapi.gunicorn:app
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

function tests {
    # Without 'python -m' fails, probably due to no __init__.py files.
    python -m pytest backend
}

function options {
    # Prints all functions in the file.
    compgen -A function
}

"${@-options}"
