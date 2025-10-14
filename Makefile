.ONESHELL:
.PHONY: all

install:
	pip install uv
	uv lock
	uv sync

dependencies:
	uv lock
	uv sync

lint:
	black . && ruff check .
	djhtml mousemetrics/. && djcss mousemetrics/.

workflows:
	pre-commit install
	pre-commit run --all-files
