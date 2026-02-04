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

lint:
	uv run black . && uv run ruff check .
	npm run prettier && uv run djcss $$(find mousemetrics/. -name "*.css" ! -path "*/staticfiles/*" ! -path "*/static/dist/styles.css") #scoping to prevent temp file scans

run-tailwind:
	npm run tailwind

workflows:
	uv run pre-commit install
	uv run pre-commit run --all-files

# Development server (no MailDev needed)
dev:
	uv run python mousemetrics/manage.py runserver
