# frozen_string_literal: true

require "minitest/autorun"
require "tmpdir"
require_relative "../tools/clean_room_tool"

class CleanRoomToolTest < Minitest::Test
  def test_packet_is_allowlisted_and_hash_verified
    Dir.mktmpdir do |dir|
      CleanRoom.build(dir)
      assert_equal CleanRoom::PACKET_FILES, Dir.children(dir).sort
      assert_empty CleanRoom.validate_packet(dir)
      refute_includes Dir.children(dir), "AI_Pacing_Canonical_Spec_v0.1.md"
      refute_includes Dir.children(dir), "minimal-reconstruction.md"
      refute_includes Dir.children(dir), "evaluation-rubric.yaml"
      packet_text = Dir.children(dir).map { |name| File.read(File.join(dir, name)) }.join("\n")
      refute_includes packet_text, "Minimal Reconstruction Prompt"
      refute_includes packet_text, "A rendering that contradicts this paragraph"
    end
  end

  def test_tampering_is_detected
    Dir.mktmpdir do |dir|
      CleanRoom.build(dir)
      File.open(File.join(dir, "source.yaml"), "a") { |file| file.write("\n# mutation\n") }
      assert CleanRoom.validate_packet(dir).any? { |error| error.include?("digest mismatch for source.yaml") }
    end
  end

  def test_unexpected_file_prevents_rebuild
    Dir.mktmpdir do |dir|
      File.write(File.join(dir, "prior-summary.md"), "contamination")
      error = assert_raises(ArgumentError) { CleanRoom.build(dir) }
      assert_includes error.message, "unexpected files"
    end
  end

  def test_editorial_reference_exposes_current_yaml_drift
    audit = CleanRoom.audit
    assert_equal 43, audit["markdown_node_count"]
    assert_equal 29, audit["yaml_node_count"]
    assert_includes audit["missing_from_yaml"], "D17"
    assert_includes audit["missing_from_yaml"], "H6"
    assert_includes audit["missing_from_yaml"], "Q10"
    assert_includes audit["extra_in_yaml"], "I7"
    assert audit["title_mismatches"].any? { |item| item["id"] == "D1" }
  end

  def test_complete_model_output_passes_deterministic_preflight
    spec = AIPacing.load_spec
    nodes = AIPacing.nodes_by_id(spec).values
    coverage = {
      "source_semantic_sha256" => AIPacing.semantic_digest(spec),
      "relationship_claim" => "faithful_reconstruction",
      "covered_nodes" => nodes.map do |node|
        {"id" => node["id"], "rendering_section" => "Overview", "paraphrase" => node["statement"]}
      end,
      "omitted_nodes" => [],
      "declared_deviations" => [],
      "added_inferences" => [],
      "uncertainty_treatment" => nodes.select { |node| node["kind"] == "hypothesis" }.map do |node|
        {"id" => node["id"], "treatment" => "Presented as uncertain and falsifiable."}
      end
    }
    Dir.mktmpdir do |dir|
      File.write(File.join(dir, "rendering.md"), (["word"] * 1200).join(" "))
      File.write(File.join(dir, "coverage.yaml"), YAML.dump(coverage))
      assert_empty CleanRoom.validate_output(dir)
    end
  end

  def test_preflight_detects_silent_omission_and_wrong_digest
    spec = AIPacing.load_spec
    coverage = {
      "source_semantic_sha256" => "0" * 64,
      "relationship_claim" => "faithful_reconstruction",
      "covered_nodes" => [],
      "omitted_nodes" => [],
      "declared_deviations" => [],
      "added_inferences" => [],
      "uncertainty_treatment" => []
    }
    Dir.mktmpdir do |dir|
      File.write(File.join(dir, "rendering.md"), (["word"] * 1200).join(" "))
      File.write(File.join(dir, "coverage.yaml"), YAML.dump(coverage))
      errors = CleanRoom.validate_output(dir)
      assert_includes errors, "source semantic digest mismatch"
      assert errors.any? { |error| error.include?("nodes neither covered nor omitted") }
    end
  end
end
