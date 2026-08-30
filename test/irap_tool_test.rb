# frozen_string_literal: true

require "minitest/autorun"
require_relative "../tools/irap_tool"

class IRAPToolTest < Minitest::Test
  def test_repository_metadata_is_registry_ready
    assert_empty IRAPReadiness.validate
  end

  def test_identity_and_planned_mirror_are_stable
    manifest = IRAPReadiness.load_yaml(IRAPReadiness::MANIFEST)
    assert_equal "https://ideas.proximitytoprogress.com/ideas/ai-pacing", manifest.dig("idea", "id")
    assert_equal "refs/heads/main", manifest.dig("repository", "canonical_ref")
    assert_includes manifest.dig("repository", "mirrors"), "https://github.com/uncomposed/ai-pacing.git"
  end

  def test_clean_room_claim_is_recognizable
    manifest = IRAPReadiness.load_yaml(IRAPReadiness::MANIFEST)
    policy_path = File.join(IRAPReadiness::ROOT, manifest.dig("verification", "policy_path"))
    policy = IRAPReadiness.load_yaml(policy_path)
    claim = policy.dig("claims", "clean_room_reconstruction")
    refute_nil claim
    assert_equal "any_one_pass", claim.dig("recognition", "rule", "type")
  end
end
