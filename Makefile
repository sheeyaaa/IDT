.PHONY: install lint typecheck test check run

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy src

test:
	pytest

check: lint typecheck test

run:
	tcgen run --prd $(PRD) --out $(OUT)
