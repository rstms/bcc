# common - initialization, variables, functions

.PHONY: showvars

# set make variables from project files
project := $(shell tq -r .project.name pyproject.toml)
module := $(shell tq -r .tool.flit.module.name pyproject.toml)
version := $(shell cat VERSION)
src_dirs := $(module) tests
makefiles := Makefile $(wildcard make/*.mk)
python_src := $(foreach dir,$(src_dirs),$(wildcard $(dir)/*.py))
other_src := $(makefiles) pyproject.toml
src := $(python_src) $(other_src)
git_commit := $(shell git log -1 | awk '/^commit/{print $$2}')
cli := $(shell tq -r '.project.scripts|keys|.[0]' pyproject.toml)
fqdn := $(shell hostname 2>/dev/null --fqdn || cat /etc/myname)

# sanity checks
$(if $(project),,$(error failed to read project name from pyproject.toml))
$(if $(shell [ -d ../"$(project)" ] || echo X),$(error project dir $(project) not found))
$(if $(shell [ $$(readlink -f ../$(project)) = $$(readlink -f .) ] || echo X),$(error mismatch: $(project) != .))
$(if $(module),,$(error failed to read module name from pyproject.toml))
$(if $(shell [ -d "./$(module)" ] || echo missing),$(error module dir '$(module)' not found))
$(if $(shell ls $(module)/__init__.py),,$(error expected "__init__.py" in module dir '$(module)'))
$(if $(version),,$(error failed to read version from version.py))

hidden_vars := hidden_vars .DEFAULT_GOAL CURDIR MAKEFILE_LIST MAKEFLAGS SHELL BROWSER_PYSCRIPT BUMPVERSION_CFG

names:
	@echo project=$(project)
	@echo module=$(module)
	@echo cli=$(cli)
	@echo version=$(version)
	@echo wheel=$(wheel)
	@echo git_commit=$(git_commit)
	@echo fqdn=$(fqdn)

showvars:
	$(foreach var,\
	    $(sort $(filter-out $(hidden_vars),$(.VARIABLES))),\
	    $(if $(filter-out recursive%,$(flavor $(var))),\
	    	$(if $(filter file%,$(origin $(var))),\
	    		$(info $(var)=$($(var)))\
	    	,)\
	    ,)\
	)
	@:
	
### list make targets with descriptions
help:	
	@set -e;\
	echo;\
	echo 'Target        | Description';\
	echo '------------- | --------------------------------------------------------------';\
	for FILE in $(makefiles); do\
	  awk <$$FILE  -F':' '\
	    BEGIN {help="begin"}\
	    /^##.*/ { help=$$0; }\
	    /^[a-z-]*:/ { if (last==help){ printf("%-14s| %s\n", $$1, substr(help,4));} }\
	    /.*/{ last=$$0 }\
	  ';\
	done;\
	echo

short-help:
	@echo "\nUsage: make TARGET\n";\
	echo $$($(MAKE) --no-print-directory help | tail +4 | awk -F'|' '{print $$1}'|sort)|fold -s -w 60;\
	echo

# add the cli help to the README
README.md: $(module)/cli.py
	awk <$@ >README.new -v flag=0 '/^## CLI/{flag=1} /```/{if(flag) exit} {print $$0}';\
	echo '```' >>README.new;\
	$(cli) --help >>README.new;\
	echo '```' >>README.new;\
	mv README.new $@;\

#
# --- functions ---
#

# break with an error if there are uncommited changes
define gitclean =
	$(if $(and $(if $(ALLOW_DIRTY),,1),$(shell git status --porcelain)),$(error git status: dirty, commit and push first))
endef

# require user confirmation   example: $(call verify_action,do something destructive)
define verify_action =
	$(if $(shell \
	read -p 'About to $(1). Confirm? [no] :' OK;\
	echo $$OK|grep '^[yY][eE]*[sS]*$$'\
	),$(info Confirmed),$(error Cowardly refusing))
endef

# break if not in virtualenv (override with make require_virtualenv=no <TARGET>)
ifndef virtualenv
  virtualenv = $(if $(filter $(require_virtualenv),no),not required,$(shell which python | grep -E virt\|venv))
  $(if $(virtualenv),,$(error virtualenv not detected))
endif

# github repo latest release version

# make clean targets
make-clean:
	@$(MAKE) --no-print-directory $(addsuffix -clean,$(notdir $(basename $(wildcard make/*.mk))))

common-clean:
	rm -f .pyproject.toml.*
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -name '*~' -exec rm -f {} +

common-sterile:
	@:

make-sterile:
	@$(MAKE) --no-print-directory $(addsuffix -sterile,$(notdir $(basename $(wildcard make/*.mk))))

