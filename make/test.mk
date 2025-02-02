# python test makefile 
test_cases := $(if $(test),-k $(test),)

test_env := env TESTING=1 DEBUG=1

ifdef ENABLE_SLOW_TESTS
pytest_opts := $(pytest_opts) --run_slow
endif

ifdef SHOW_FIXTURES
pytest_opts := $(pytest_opts) --setup-show
endif


### list tests
testls:
	@testls

### regression test
test: fmt
	$(test_env) pytest $(pytest_opts) --log-cli-level=WARNING $(test_cases)

### pytest with break to debugger
debug: fmt
	$(test_env) DEBUG=1 pytest $(pytest_opts) -sv --pdb --log-cli-level=INFO $(test_cases)

### check code coverage quickly with the default Python
coverage:
	coverage run --source $(module) -m pytest
	coverage report -m

test-clean:
	rm -f .coverage

test-sterile: test-clean
	@:
