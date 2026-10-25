.PHONY: check validate accept generate test clean-room clean-room-audit systems-check systems-report assumptions-check assumptions-report modes-check modes-report evidence-check evidence-report units-check units-report

# The tools read UTF-8 sources; without a UTF-8 locale Ruby defaults to US-ASCII.
export LANG := C.UTF-8

check: test systems-check assumptions-check modes-check evidence-check units-check
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
	@python3 research_notes/external/ai-futures-model/tests/test_aifm.py
	@python3 "research_notes/Off Earth industry as misalignment control/model/tests/test_check_tolerances.py"
	@python3 test/evidence_tool_test.py
	@python3 test/units_tool_test.py
	@python3 research_notes/external/units-bridge/tests/test_units_bridge.py
	@python3 "research_notes/Off Earth industry as misalignment control/model/tests/test_measure_sensitivity.py"
	@python3 research_notes/external/epoch-gate/tests/test_epoch_gate.py
	@python3 research_notes/external/hugging-face-incident/test_hf_incident.py

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

evidence-check:
	@python3 tools/evidence_tool.py check

evidence-report:
	@python3 tools/evidence_tool.py report

units-check:
	@python3 tools/units_tool.py check

units-report:
	@python3 tools/units_tool.py report
