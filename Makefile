.PHONY: check validate accept generate test clean-room clean-room-audit systems-check systems-report assumptions-check assumptions-report modes-check modes-report

# The tools read UTF-8 sources; without a UTF-8 locale Ruby defaults to US-ASCII.
export LANG := C.UTF-8

check: test systems-check assumptions-check modes-check
	@ruby tools/spec_tool.rb check

validate:
	@ruby tools/spec_tool.rb validate

accept:
	@ruby tools/spec_tool.rb accept

generate:
	@ruby tools/spec_tool.rb generate

test:
	@ruby test/spec_tool_test.rb
	@ruby test/rendering_tool_test.rb
	@ruby test/clean_room_tool_test.rb
	@ruby test/irap_tool_test.rb
	@ruby test/registry_payload_test.rb
	@python3 test/json_schema_test.py
	@python3 test/systems_tool_test.py
	@python3 test/assumptions_tool_test.py
	@python3 test/modes_tool_test.py

systems-check:
	@python3 tools/systems_tool.py check

systems-report:
	@python3 tools/systems_tool.py report

assumptions-check:
	@python3 tools/assumptions_tool.py check

assumptions-report:
	@python3 tools/assumptions_tool.py report

clean-room:
	@ruby tools/clean_room_tool.rb build

clean-room-audit:
	@ruby tools/clean_room_tool.rb audit

modes-check:
	@python3 tools/modes_tool.py check

modes-report:
	@python3 tools/modes_tool.py report
	@python3 tools/modes_tool.py compare
