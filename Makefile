.PHONY: check fast run
check:
	./check.sh
fast:
	./check.sh fast
run:
	python -m app
