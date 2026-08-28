.PHONY: help install sync run demo verify test eval eval-live coverage lint fmt \
        docker-build docker-up docker-down compose-config \
        k8s-build k8s-apply outage load

ROOT := $(CURDIR)
UV := uv

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install sync: ## Install dependencies with uv
	$(UV) sync --all-extras

run: ## Start API locally (demo mode)
	$(UV) run uvicorn agent_gateway.main:app --host 0.0.0.0 --port 8000 --reload

demo: ## Run eight-step portfolio demo
	$(UV) run python scripts/demo.py

verify: ## Lint, test, and evaluation thresholds
	$(UV) run python scripts/verify.py

test: ## Run pytest
	$(UV) run python -m pytest -q

eval: ## Run deterministic golden-set evaluation (CI gate)
	$(UV) run python scripts/evaluate.py

eval-live: ## Optional live-provider evaluation (requires API keys)
	$(UV) run python scripts/evaluate_live.py

coverage: ## Run tests with HTML coverage report
	$(UV) run python -m coverage run -m pytest -q
	$(UV) run python -m coverage report
	$(UV) run python -m coverage html -d htmlcov
	@echo "Coverage HTML report: htmlcov/index.html"

lint: ## Ruff lint + format check
	$(UV) run ruff format --check .
	$(UV) run ruff check .

fmt: ## Auto-format with Ruff
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

outage: ## Simulate primary provider outage
	$(UV) run python scripts/simulate_outage.py

load: ## Run Locust load test (API must be running)
	$(UV) run locust -f tests/load/locustfile.py --host http://localhost:8000

docker-build: ## Build container image
	docker build -t enterprise-agent-gateway:local .

docker-up: ## Start API + Prometheus + Grafana
	docker compose up --build -d

docker-down: ## Stop compose stack
	docker compose down

compose-config: ## Validate docker-compose.yml
	docker compose config

k8s-build: ## Render local Kustomize overlay
	kubectl kustomize deploy/kubernetes/overlays/local

k8s-apply: ## Apply local Kustomize overlay (requires cluster)
	kubectl apply -k deploy/kubernetes/overlays/local

tf-fmt: ## Terraform format check (aws-ecs)
	cd deploy/terraform/aws-ecs && terraform fmt -check -recursive

tf-validate: ## Terraform validate (aws-ecs, no backend)
	cd deploy/terraform/aws-ecs && terraform init -backend=false && terraform validate

seed: ## Seed synthetic CRE database
	$(UV) run python scripts/seed_data.py
