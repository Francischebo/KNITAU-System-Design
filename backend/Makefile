.PHONY: test lint contracts schema migrate run

test:
	pytest --cov=apps --cov-report=term-missing

lint:
	ruff check .
	mypy apps config
	bandit -r apps config -q

contracts:
	lint-imports

schema:
	python manage.py spectacular --color --file openapi-schema.yaml

migrate:
	python manage.py makemigrations
	python manage.py migrate

run:
	python manage.py runserver 0.0.0.0:8000
