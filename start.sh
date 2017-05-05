#!/bin/bash

BASEDIR="$(dirname $0)"
eval "$(~/.pyenv/bin/pyenv init -)"
eval "$(~/.pyenv/bin/pyenv virtualenv-init -)"
export PYENV_VERSION='home-auto'

export PYTHONUNBUFFERED=1
exec python ${BASEDIR}/whistle.py
