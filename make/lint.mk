# python lint makefile

LINT_MAX_COMPLEXITY ?= 12
LINT_LINE_LENGTH ?= 120
LINT_IGNORE ?= E203

LINT_PYTHON_VERSION != python --version | sed 's/Python \([0-9]*\)\.\([0-9]*\).*/\1\2/'
ignore_errors := $(if $(LINT_IGNORE),--extend-ignore $(LINT_IGNORE),)
 
ISORT_OPTS = --py $(LINT_PYTHON_VERSION) --profile black
BLACK_OPTS = --target-version py$(LINT_PYTHON_VERSION) --line-length $(LINT_LINE_LENGTH)
FLAKE8_OPTS = --max-line-length $(LINT_LINE_LENGTH) --max-complexity $(LINT_MAX_COMPLEXITY) $(ignore_errors)

export ISORT_OPTS
export BLACK_OPTS
export FLAKE8_OPTS

.fmt: $(python_src)
	isort $(ISORT_OPTS) $(src_dirs)
	black $(BLACK_OPTS) $(src_dirs)
	flake8 $(FLAKE8_OPTS) $(src_dirs)
	touch $@

### format source and lint
fmt:	.fmt

### vim autofix
fix:
	fixlint $(src_dirs)

lint-clean:
	rm -f .black .flake8 .errors .fmt

lint-sterile:
	@:
