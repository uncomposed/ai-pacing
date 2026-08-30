.PHONY: check validate accept generate test clean-room clean-room-audit

check: test
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
	@python3 test/json_schema_test.py

clean-room:
	@ruby tools/clean_room_tool.rb build

clean-room-audit:
	@ruby tools/clean_room_tool.rb audit
