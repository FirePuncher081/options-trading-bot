PYTHON ?= python

.PHONY: setup research check notebooks dashboard collect
setup:
	$(PYTHON) -m pip install -r requirements.lock
	$(PYTHON) -m pip check

research:
	$(PYTHON) -m options_lab research --backtest-config config/backtest.json
	$(PYTHON) dashboard/build_data.py
	$(PYTHON) dashboard/render_charts.py

check:
	$(PYTHON) -m compileall -q options_lab dashboard scripts
	$(PYTHON) -m pytest -q
	$(PYTHON) scripts/check_notebooks.py
	npm test

notebooks:
	cd notebooks && jupyter lab

dashboard:
	$(PYTHON) -m http.server 8080 --bind 127.0.0.1

collect:
	$(PYTHON) -m options_lab collect
