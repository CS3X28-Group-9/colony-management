.ONESHELL:
.PHONY: all

install:
	pip install uv
	uv lock
	uv sync

dependencies:
	uv lock
	uv sync


	uv run black . && uv run ruff check .
	uv run djhtml mousemetrics/. && uv run djcss mousemetrics/. #scoping to prevent temp file scans

workflows:
	uv run pre-commit install
	uv run pre-commit run --all-files
	
run-tailwind:
	npm run tailwind
