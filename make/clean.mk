# make clean targets

.PHONY: clean sterile clean-clean clean-sterile

### remove all build, test, coverage and Python artifacts
clean: $(addsuffix -clean,$(notdir $(basename $(wildcard make/*.mk))))

### remove all generated files
sterile: $(addsuffix -sterile,$(notdir $(basename $(wildcard make/*.mk))))

# clean all
clean-clean: 
	rm -rf build/ *.log
	find dist -not -name README.md -not -name dist -exec rm -f '{}' +
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -f {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

clean-sterile: clean-clean
