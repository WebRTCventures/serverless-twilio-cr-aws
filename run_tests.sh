#!/bin/bash
pip install -r tests/requirements-test.txt
python -m pytest tests/websocket/ -v