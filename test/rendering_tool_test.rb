# frozen_string_literal: true

require "minitest/autorun"
require_relative "../tools/rendering_tool"

class RenderingToolTest < Minitest::Test
  EXAMPLE = File.join(AIPacing::ROOT, "examples", "renderings", "minimal-reconstruction.yaml")

  def setup
    @manifest = AIPacingRendering.load_manifest(EXAMPLE)
  end

  def copy_manifest
    Marshal.load(Marshal.dump(@manifest))
  end

  def test_example_targets_and_hashes_an_exact_historical_artifact
    assert_empty AIPacingRendering.validate(@manifest)
  end

  def test_branch_name_is_not_a_verification_target
    mutated = copy_manifest
    mutated["rendering"]["renders"]["git_commit"] = "main"
    errors = AIPacingRendering.validate(mutated, verify_git: false)
    assert errors.any? { |error| error.include?("full 40-hex") }
  end

  def test_unknown_covered_node_is_rejected_against_target_commit
    mutated = copy_manifest
    mutated["rendering"]["relationship"]["covers"] << "K999"
    errors = AIPacingRendering.validate(mutated)
    assert errors.any? { |error| error.include?("unknown target node K999") }
  end

  def test_faithful_claim_must_cover_entire_kernel
    mutated = copy_manifest
    mutated["rendering"]["relationship"]["covers"].delete("K7")
    errors = AIPacingRendering.validate(mutated)
    assert errors.any? { |error| error.include?("does not cover kernel nodes K7") }
  end

  def test_artifact_digest_is_verified_at_target_commit
    mutated = copy_manifest
    mutated["rendering"]["artifact_digest"] = "sha256:#{'0' * 64}"
    errors = AIPacingRendering.validate(mutated)
    assert errors.any? { |error| error.include?("artifact digest mismatch") }
  end
end
