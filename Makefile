.ONESHELL:
.PHONY: all install dependencies lint workflows dev

install:
	pip install uv
	uv lock
	uv sync
	npm i

dependencies:
	uv lock
	uv sync
	uv run djhtml mousemetrics/. && uv run djcss mousemetrics/.

lint:
	uv run black . && uv run ruff check .
	uv run djhtml mousemetrics/. && uv run djcss mousemetrics/. #scoping to prevent temp file scans

workflows:
	uv run pre-commit install
	uv run pre-commit run --all-files

run-tailwind:
	npm run tailwind
# Development server (no MailDev needed)
dev:
	uv run python mousemetrics/manage.py runserver
