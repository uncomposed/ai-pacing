# frozen_string_literal: true

require "minitest/autorun"
require_relative "../tools/spec_tool"

class SpecToolTest < Minitest::Test
  def setup
    @spec = AIPacing.load_spec
  end

  def copy_spec
    Marshal.load(Marshal.dump(@spec))
  end

  def test_canonical_spec_is_valid
    assert_empty AIPacing.validate(@spec)
  end

  def test_all_acceptance_tests_pass
    results = AIPacing.evaluate_acceptance(@spec)
    assert results.all? { |result| result["passed"] }, results.inspect
  end

  def test_semantic_digest_is_stable_under_mapping_reordering
    reordered = @spec.to_a.reverse.to_h
    assert_equal AIPacing.semantic_digest(@spec), AIPacing.semantic_digest(reordered)
  end

  def test_dangling_relation_is_rejected
    mutated = copy_spec
    mutated["relations"] << {"from" => "K1", "to" => "D999", "type" => "grounds"}
    assert AIPacing.validate(mutated).any? { |error| error.include?("unknown to D999") }
  end

  def test_dependency_cycle_is_rejected
    mutated = copy_spec
    mutated["relations"] << {"from" => "I4", "to" => "K7", "type" => "grounds"}
    assert AIPacing.validate(mutated).any? { |error| error.include?("dependency cycle") }
  end

  def test_hypothesis_without_falsifier_is_rejected
    mutated = copy_spec
    mutated["nodes"].find { |node| node["id"] == "H1" }.delete("falsifier")
    assert AIPacing.validate(mutated).any? { |error| error == "hypothesis H1 missing falsifier" }
  end

  def test_optional_policy_cannot_be_promoted_silently
    mutated = copy_spec
    mutated["nodes"].find { |node| node["id"] == "I7" }["replaceable"] = false
    assert AIPacing.validate(mutated).any? { |error| error.include?("I7 must declare replaceable") }
  end

  def test_unknown_provenance_source_is_rejected
    mutated = copy_spec
    mutated["nodes"].find { |node| node["id"] == "K1" }["provenance"]["sources"] << "SRC-NOT-REAL"
    assert AIPacing.validate(mutated).any? { |error| error.include?("unknown source SRC-NOT-REAL") }
  end

  def test_kernel_mutation_breaks_acceptance_checksum
    mutated = copy_spec
    mutated["nodes"].find { |node| node["id"] == "K7" }["kind"] = "derived"
    result = AIPacing.evaluate_acceptance(mutated).find { |item| item["id"] == "AT-001" }
    refute result["passed"]
  end

  def test_expected_deterministic_views_are_rendered
    expected = @spec["deterministic_views"].map { |view| view["path"] }.sort
    assert_equal expected, AIPacing.render_views(@spec).keys.sort
  end

  def test_impact_analysis_reaches_legal_and_physical_controls
    impact = AIPacing.transitive_impact(@spec, "K7")
    assert_includes impact, "I2"
    assert_includes impact, "I4"
    assert_includes impact, "I5"
  end
end
