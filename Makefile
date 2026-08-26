.PHONY: install run debug clean lint

install:
	uv sync

run:
	@PYGAME_HIDE_SUPPORT_PROMPT=1 uv run python -m fly_in $(MAP)

debug:
	uv run python -m pdb -m fly_in $(MAP)

clean:
	rm -rf __pycache__ .mypy_cache fly_in/__pycache__

lint:
	uv run flake8 fly_in/
	uv run mypy fly_in/ --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
