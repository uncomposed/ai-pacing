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

  def test_off_earth_convergence_is_not_origin_provenance
    source_id = "SRC-POTAPOV-OFF-EARTH"
    event = @spec["audit_events"].find { |item| item["id"] == "EVT-2026-OFF-EARTH-CONVERGENCE" }

    assert_includes event["evidence"], source_id
    assert_equal "external-convergence", event["phase"]
    refute @spec["nodes"].any? { |node| Array(node.dig("provenance", "sources")).include?(source_id) }
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

  # Proposed nodes: recorded for review, never counted as accepted canon.

  def proposed_node(id, kind, extra = {})
    {
      "id" => id, "kind" => kind, "title" => "Mutation #{id}", "statement" => "Mutation.",
      "proposal" => {"issue" => "uncomposed/ai-pacing#999"},
      "provenance" => {
        "origin" => "test", "sources" => ["SRC-PLAN-A-BARGAINING"], "ai_roles" => ["drafting"],
        "author_status" => "proposed"
      }
    }.merge(extra)
  end

  # The proposed-node list is derived from the registry, not pinned here, so
  # two proposal branches do not conflict on this test.
  def registry_proposed_ids
    registry["ids"].select { |item| item["definitions"].any? { |d| d["source"] == "yaml" && d["status"] == "proposed" } }
                   .map { |item| item["id"] }.sort
  end

  def test_canonical_spec_records_issue_22_editor_decisions
    nodes = AIPacing.nodes_by_id(@spec)
    refute_empty registry_proposed_ids
    assert_equal registry_proposed_ids, AIPacing.proposed_ids(@spec)
    {
      "H10" => "accepted-as-hypothesis", "H14" => "accepted-as-hypothesis", "I11" => "accepted-as-option",
      "Q11" => "unresolved", "Q12" => "unresolved", "Q13" => "unresolved"
    }.each do |id, status|
      assert_equal status, nodes[id].dig("provenance", "author_status"), id
      refute_nil nodes[id]["proposal"], "#{id} keeps its proposal issue as a record"
    end
    assert_nil nodes["D18"]
    assert_nil nodes["D19"]
    refute_includes nodes["I11"]["implements"], "H10"
  end

  def test_proposed_kernel_does_not_count_as_canon
    mutated = copy_spec
    mutated["nodes"] << proposed_node("K8", "kernel")
    assert_empty AIPacing.validate(mutated)
    result = AIPacing.evaluate_acceptance(mutated).find { |item| item["id"] == "AT-001" }
    assert result["passed"], result.inspect
    assert_equal %w[K1 K2 K3 K4 K5 K6 K7], AIPacing.accepted_kernel_ids(mutated)
    refute_includes AIPacing.render_minimal(mutated), "K8"
    refute_includes AIPacing.render_review_checklist(mutated), "K8"
  end

  def test_proposed_node_cannot_satisfy_identity_or_path_assertions
    mutated = copy_spec
    node = mutated["nodes"].find { |item| item["id"] == "I11" }
    node["provenance"]["author_status"] = "proposed"
    node["proposal"] = {"issue" => "uncomposed/ai-pacing#999"}
    assert_empty AIPacing.validate(mutated)
    result = AIPacing.evaluate_acceptance(mutated).find { |item| item["id"] == "AT-006" }
    refute result["passed"]
    assert_includes result["failures"].join, "K7 -> I11"
  end

  def test_proposed_hypothesis_still_needs_falsifier
    mutated = copy_spec
    mutated["nodes"].find { |node| node["id"] == "H15" }.delete("stopping_rule")
    assert_includes AIPacing.validate(mutated), "hypothesis H15 missing stopping_rule"
    result = AIPacing.evaluate_acceptance(mutated).find { |item| item["id"] == "AT-007" }
    refute result["passed"]
  end

  def test_proposed_node_must_name_its_issue
    mutated = copy_spec
    mutated["nodes"].find { |node| node["id"] == "H15" }.delete("proposal")
    assert_includes AIPacing.validate(mutated), "proposed node H15 must name its proposal issue"
  end

  def test_unknown_author_status_is_rejected
    mutated = copy_spec
    mutated["nodes"].find { |node| node["id"] == "K1" }["provenance"]["author_status"] = "endorsed"
    assert AIPacing.validate(mutated).any? { |error| error.include?("unknown author_status") }
  end

  def test_accepted_node_cannot_depend_on_proposed_node
    mutated = copy_spec
    mutated["nodes"].find { |node| node["id"] == "D1" }["derived_from"] << "H15"
    assert_includes AIPacing.validate(mutated), "accepted node D1 derived_from references proposed node H15"

    mutated = copy_spec
    mutated["relations"] << {"from" => "H15", "to" => "D4", "type" => "grounds"}
    assert_includes AIPacing.validate(mutated), "accepted node D4 cannot be grounded by proposed node H15"
  end

  def test_dependency_graph_marks_proposed_nodes
    graph = AIPacing.render_graph(@spec)
    assert_includes graph, "class #{registry_proposed_ids.join(',')} proposed"
  end

  # Reserved-ID registry.

  def registry
    AIPacing.load_registry
  end

  def test_registry_matches_canonical_spec_and_editorial_reference
    assert_empty AIPacing.validate_registry(@spec, registry)
  end

  def test_registry_records_renumbering_of_issue_ids
    mapping = registry["renumbering"].to_h { |row| [[row["source"], row["old"]], row["new"]] }
    assert_equal "H14", mapping[%w[issue_1 H6]]
    assert_equal "Q13", mapping[%w[issue_1 Q5]]
    assert_equal %w[H10 D18 I11 Q11 D19 Q12],
                 %w[H7 D7 I8 Q6 D8 Q7].map { |old| mapping[["issue_3", old]] }
  end

  def test_registry_renumbers_off_earth_candidates_and_prefixes_local_ids
    mapping = registry["renumbering"].to_h { |row| [[row["source"], row["old"]], row["new"]] }
    assert_equal %w[D20 D21 Q14 Q15 Q16],
                 %w[D7 D8 Q6 Q7 Q8].map { |old| mapping[["off_earth_report", old]] }
    assert registry["ids"].none? { |item| item["collision"] == "reserved-conflict" }
    registry["local_namespaces"].each do |namespace|
      assert namespace["ids"].all? { |id| id.start_with?(namespace["prefix"]) }, namespace["locator"]
    end
  end

  def test_unregistered_yaml_node_is_rejected
    mutated = copy_spec
    mutated["nodes"] << proposed_node("Q14", "open_question", "relates_to" => ["K1"])
    assert_includes AIPacing.validate_registry(mutated, registry), "registry: YAML node Q14 is not registered with a yaml definition"
  end

  def test_yaml_node_reusing_a_reserved_or_editorial_id_is_rejected
    mutated = copy_spec
    mutated["nodes"] << proposed_node("D7", "derived", "derived_from" => ["K1"])
    changed = registry
    entry = changed["ids"].find { |item| item["id"] == "D7" }
    entry["collision"] = "reserved-conflict"
    entry["definitions"] << {"source" => "yaml", "title" => "Mutation D7", "status" => "proposed"}
    errors = AIPacing.validate_registry(mutated, changed)
    assert_includes errors, "registry: D7 is a reserved conflict and cannot be used in the YAML"
    assert_includes errors, "registry: proposed YAML node D7 must not collide with another definition"

    entry["collision"] = "legacy"
    errors = AIPacing.validate_registry(mutated, changed)
    assert errors.any? { |error| error.include?("D7 cannot be a legacy collision") }, errors.inspect
  end

  def test_duplicate_registry_entry_is_rejected
    changed = registry
    changed["ids"] << Marshal.load(Marshal.dump(changed["ids"].find { |item| item["id"] == "H10" }))
    assert_includes AIPacing.validate_registry(@spec, changed), "registry: duplicate entry H10"
  end

  def test_registry_title_and_status_must_track_the_yaml
    mutated = copy_spec
    node = mutated["nodes"].find { |item| item["id"] == "H15" }
    node["title"] = "Retitled"
    node["provenance"]["author_status"] = "accepted-as-hypothesis"
    errors = AIPacing.validate_registry(mutated, registry)
    assert_includes errors, "registry: H15 yaml title differs from YAML node title"
    assert_includes errors, "registry: H15 yaml status proposed differs from YAML (accepted)"
  end

  def test_withdrawn_ids_stay_registered_without_a_yaml_node
    definition = registry["ids"].find { |item| item["id"] == "D18" }["definitions"].first
    assert_equal "withdrawn", definition["status"]
    assert_equal "H15", definition["superseded_by"]
    assert_equal "H2", registry["ids"].find { |item| item["id"] == "D19" }["definitions"].first["superseded_by"]

    mutated = copy_spec
    mutated["nodes"] << proposed_node("D18", "derived", "title" => definition["title"])
    errors = AIPacing.validate_registry(mutated, registry)
    assert_includes errors, "registry: withdrawn D18 still has a YAML node"
    assert_includes errors, "registry: D18 yaml status withdrawn differs from YAML (proposed)"
  end

  def test_withdrawal_needs_a_reason_and_a_registered_successor
    changed = registry
    definition = changed["ids"].find { |item| item["id"] == "D18" }["definitions"].first
    definition.delete("withdrawn_reason")
    definition["superseded_by"] = "H99"
    errors = AIPacing.validate_registry(@spec, changed)
    assert_includes errors, "registry: withdrawn D18 needs a withdrawn_reason"
    assert_includes errors, "registry: D18 superseded_by H99 is not registered"

    changed = registry
    changed["ids"].find { |item| item["id"] == "H15" }["definitions"].first["superseded_by"] = "H2"
    assert_includes AIPacing.validate_registry(@spec, changed),
                    'registry: H15 has withdrawal fields but status "proposed"'
  end

  def test_legacy_ceiling_must_be_above_every_legacy_id
    changed = registry
    changed["legacy_ceiling"]["H"] = "H12"
    assert_includes AIPacing.validate_registry(@spec, changed),
                    "registry: legacy_ceiling H12 is not above every legacy H ID"
  end

  def issue_numbered_entry(id, kind, status = "proposed")
    {"id" => id, "kind" => kind, "collision" => "none",
     "definitions" => [{"source" => "yaml", "title" => "Mutation #{id}", "status" => status}]}
  end

  def test_issue_numbered_id_must_be_proposed_in_the_issue_with_that_number
    changed = registry
    changed["ids"] << issue_numbered_entry("H95", "hypothesis")
    mutated = copy_spec
    mutated["nodes"] << proposed_node("H95", "hypothesis", "proposal" => {"issue" => "uncomposed/ai-pacing#91"})
    errors = AIPacing.validate_registry(mutated, changed)
    assert_includes errors, 'registry: issue-numbered H95 must be proposed in uncomposed/ai-pacing#95, found "uncomposed/ai-pacing#91"'

    mutated["nodes"].last["proposal"] = {"issue" => "uncomposed/ai-pacing#95"}
    assert_empty AIPacing.validate_registry(mutated, changed)
  end

  def test_reserved_issue_numbered_id_needs_its_issue_as_source
    changed = registry
    changed["ids"] << {"id" => "Q97", "kind" => "open_question", "collision" => "none",
                       "definitions" => [{"source" => "issue_91", "title" => "Mutation", "status" => "reserved"}]}
    assert_includes AIPacing.validate_registry(@spec, changed),
                    "registry: issue-numbered Q97 needs a definition from source issue_97 or a YAML node proposed in uncomposed/ai-pacing#97"
  end

  def test_id_between_the_legacy_ceiling_and_the_first_issue_number_is_rejected
    changed = registry
    changed["ids"] << {"id" => "H50", "kind" => "hypothesis", "collision" => "none",
                       "definitions" => [{"source" => "issue_91", "title" => "Mutation", "status" => "reserved"}]}
    assert_includes AIPacing.validate_registry(@spec, changed),
                    "registry: H50 is neither a legacy ID below H17 nor an issue-numbered ID at or above H93"
  end

  def test_issue_id_command_allocates_from_the_issue_number
    assert_equal "H95", AIPacing.issue_id("H", "95", registry)
    assert_equal "I95", AIPacing.issue_id("i", 95, registry)
    error = assert_raises(ArgumentError) { AIPacing.issue_id("H", 91, registry) }
    assert_match(/below 93/, error.message)
    changed = registry
    changed["ids"] << issue_numbered_entry("H95", "hypothesis")
    error = assert_raises(ArgumentError) { AIPacing.issue_id("H", 95, changed) }
    assert_match(/already registered/, error.message)
    assert_raises(ArgumentError) { AIPacing.issue_id("X", 95, registry) }
  end

  def test_unregistered_editorial_heading_is_rejected
    changed = registry
    changed["ids"].reject! { |item| item["id"] == "D17" }
    assert_includes AIPacing.validate_registry(@spec, changed), "registry: editorial reference ID D17 is not registered"
  end

  def test_impact_analysis_reaches_legal_and_physical_controls
    impact = AIPacing.transitive_impact(@spec, "K7")
    assert_includes impact, "I2"
    assert_includes impact, "I4"
    assert_includes impact, "I5"
  end
end
