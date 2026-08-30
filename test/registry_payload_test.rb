# frozen_string_literal: true

require "minitest/autorun"
require_relative "../tools/registry_payload"

class RegistryPayloadTest < Minitest::Test
  def test_idea_payload_targets_current_full_commit
    payload = RegistryPayload.idea("a" * 40)
    assert_equal "ai-pacing", payload["slug"]
    assert_equal RegistryPayload::REPOSITORY, payload["repository"]
    assert_equal({"algorithm" => "sha1", "value" => "a" * 40}, payload["git_commit"])
    assert_includes payload["spec_yaml"], "id: ai-pacing"
  end

  def test_dependency_map_payload_preserves_artifact_and_target_digests
    payload = RegistryPayload.dependency_map
    assert_match(/\Asha256:[0-9a-f]{64}\z/, payload.dig("artifact", "digest"))
    assert_match(/\A[0-9a-f]{40}\z/, payload.dig("target", "revision"))
    assert_equal RegistryPayload::REPOSITORY, payload.dig("target", "repository")
  end
end
