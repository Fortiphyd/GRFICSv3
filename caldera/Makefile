.PHONY: help
help: ## print this help message
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_/-]+:.*?## .*$$' | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.PHONY: build/windows
build/windows: ## build the payload for Windows
	docker run --volume "`pwd`:/src/" batonogov/pyinstaller-windows:latest

.PHONY: build/linux
build/linux: ## build the payload for Linux
	docker run --volume "`pwd`:/src/" batonogov/pyinstaller-linux:main-slim-bullseye

.PHONY: build/local
build/local: ## build the payload in the local environment
	pyinstaller -F modbus_cli.py --collect-all pymodbus

.PHONY: update
update: ## update payloads
	cp dist/* ../payloads
