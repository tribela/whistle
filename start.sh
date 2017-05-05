#!/bin/bash

BASEDIR="$(dirname $0)"
eval "$(~/.pyenv/bin/pyenv init -)"
eval "$(~/.pyenv/bin/pyenv virtualenv-init -)"
export PYENV_VERSION='home-auto'

python ${BASEDIR}/whistle.py
