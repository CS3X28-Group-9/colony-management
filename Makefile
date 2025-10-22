.ONESHELL:
.PHONY: all install dependencies lint workflows run-tailwind maildev dev

install:
	pip install uv
	uv lock
	uv sync

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

maildev:
	npm install -g maildev
	nohup maildev >/dev/null 2>&1 &

dev:
	make maildev
	uv run python mousemetrics/manage.py runserver
