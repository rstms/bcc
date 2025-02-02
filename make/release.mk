### create a new github release

.PHONY: release latest-release release-clean release-sterile

latest_release := $(shell gh release view --json tagName --jq .tagName)

.release: $(wheel)
ifeq "v$(version)" "$(latest_release)"
	@echo version $(version) is already released
else
	gh release create v$(version) --generate-notes --target master;
	gh release upload v$(version) $(wheel);
	which devpi-config && devpi-config || true
	which devpi && devpi upload $(wheel) || true
endif
	@touch $@

latest-release:
	@echo $(latest_release)

release: .release


release-clean:
	rm -f .release


release-sterile:
	@:
