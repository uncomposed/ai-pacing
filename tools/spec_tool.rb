#!/usr/bin/env ruby
# frozen_string_literal: true

require "csv"
require "date"
require "digest"
require "fileutils"
require "json"
require "set"
require "yaml"

module AIPacing
  ROOT = File.expand_path("..", __dir__)
  DEFAULT_SPEC = File.join(ROOT, "spec", "ai-pacing.yaml")
  REQUIRED_TOP_LEVEL = %w[
    specification typed_layers sources audit_events nodes relations publication
    acceptance_tests deterministic_views
  ].freeze
  NODE_REFERENCE_FIELDS = %w[derived_from supports implements relates_to].freeze
  GRAPH_RELATIONS = %w[grounds conditions implements].freeze

  module_function

  def load_spec(path = DEFAULT_SPEC)
    YAML.safe_load(File.read(path), permitted_classes: [Date], aliases: false)
  rescue Psych::Exception => e
    raise ArgumentError, "YAML parse error: #{e.message}"
  end

  def deep_sort(value)
    case value
    when Hash
      value.keys.sort_by(&:to_s).to_h { |key| [key, deep_sort(value[key])] }
    when Array
      value.map { |item| deep_sort(item) }
    when Date
      value.iso8601
    else
      value
    end
  end

  def canonical_json(spec)
    JSON.pretty_generate(deep_sort(spec)) + "\n"
  end

  def semantic_digest(spec)
    Digest::SHA256.hexdigest(JSON.generate(deep_sort(spec)))
  end

  def nodes_by_id(spec)
    Array(spec["nodes"]).to_h { |node| [node["id"], node] }
  end

  def sources_by_id(spec)
    Array(spec["sources"]).to_h { |source| [source["id"], source] }
  end

  def graph(spec)
    adjacency = Hash.new { |hash, key| hash[key] = [] }
    Array(spec["relations"]).each do |relation|
      next unless GRAPH_RELATIONS.include?(relation["type"])

      adjacency[relation["from"]] << relation["to"]
    end
    adjacency.each_value(&:sort!)
    adjacency
  end

  def path_exists?(spec, source, target)
    return true if source == target

    adjacency = graph(spec)
    visited = Set.new([source])
    queue = [source]
    until queue.empty?
      current = queue.shift
      adjacency[current].each do |neighbor|
        return true if neighbor == target
        next if visited.include?(neighbor)

        visited << neighbor
        queue << neighbor
      end
    end
    false
  end

  def value_at_path(spec, path)
    path.split(".").reduce(spec) do |value, segment|
      return nil unless value.is_a?(Hash)

      value[segment]
    end
  end

  def validate(spec)
    errors = []
    unless spec.is_a?(Hash)
      return ["root must be a mapping"]
    end

    REQUIRED_TOP_LEVEL.each do |key|
      errors << "missing top-level key #{key}" unless spec.key?(key)
    end
    return errors unless errors.empty?

    validate_specification(spec, errors)
    validate_unique_ids(spec, errors)
    validate_sources(spec, errors)
    validate_nodes(spec, errors)
    validate_audit(spec, errors)
    validate_relations(spec, errors)
    validate_acceptance_definitions(spec, errors)
    validate_views(spec, errors)
    validate_cycles(spec, errors)
    errors
  end

  def validate_specification(spec, errors)
    required = %w[id title version status purpose authority responsibility generator_contract]
    required.each do |field|
      errors << "specification missing #{field}" unless spec["specification"].key?(field)
    end
    layers = spec["typed_layers"]
    %w[kernel derived hypothesis implementation open_question].each do |kind|
      errors << "typed_layers missing #{kind}" unless layers.key?(kind)
    end
  end

  def validate_unique_ids(spec, errors)
    collections = {
      "source" => spec["sources"],
      "audit event" => spec["audit_events"],
      "node" => spec["nodes"],
      "acceptance test" => spec["acceptance_tests"],
      "view" => spec["deterministic_views"]
    }
    collections.each do |label, items|
      ids = Array(items).map { |item| item["id"] }
      errors << "#{label} with missing id" if ids.any?(&:nil?)
      ids.compact.tally.select { |_id, count| count > 1 }.each_key do |id|
        errors << "duplicate #{label} id #{id}"
      end
    end
  end

  def validate_sources(spec, errors)
    spec["sources"].each do |source|
      %w[id title kind date locator contribution].each do |field|
        errors << "source #{source['id']} missing #{field}" if blank?(source[field])
      end
    end
  end

  def validate_nodes(spec, errors)
    source_ids = sources_by_id(spec).keys.to_set
    node_ids = nodes_by_id(spec).keys.to_set
    prefixes = spec["typed_layers"].transform_values { |layer| layer["prefix"] }

    spec["nodes"].each do |node|
      id = node["id"] || "<missing>"
      %w[id kind title statement provenance].each do |field|
        errors << "node #{id} missing #{field}" if blank?(node[field])
      end
      kind = node["kind"]
      if !prefixes.key?(kind)
        errors << "node #{id} has unknown kind #{kind.inspect}"
      elsif !id.start_with?(prefixes[kind])
        errors << "node #{id} does not use #{kind} prefix #{prefixes[kind]}"
      end

      provenance = node["provenance"] || {}
      %w[origin sources ai_roles author_status].each do |field|
        errors << "node #{id} provenance missing #{field}" if blank?(provenance[field])
      end
      Array(provenance["sources"]).each do |source_id|
        errors << "node #{id} references unknown source #{source_id}" unless source_ids.include?(source_id)
      end

      NODE_REFERENCE_FIELDS.each do |field|
        Array(node[field]).each do |target|
          errors << "node #{id} #{field} references unknown node #{target}" unless node_ids.include?(target)
        end
      end

      if kind == "hypothesis"
        %w[falsifier evidence_needed stopping_rule].each do |field|
          errors << "hypothesis #{id} missing #{field}" if blank?(node[field])
        end
      end
      if kind == "implementation" && node["replaceable"] != true
        errors << "implementation #{id} must declare replaceable: true"
      end
    end
  end

  def validate_audit(spec, errors)
    source_ids = sources_by_id(spec).keys.to_set
    node_ids = nodes_by_id(spec).keys.to_set
    spec["audit_events"].each do |event|
      id = event["id"] || "<missing>"
      %w[id date phase summary evidence affected_nodes confidence].each do |field|
        errors << "audit event #{id} missing #{field}" if blank?(event[field])
      end
      Array(event["evidence"]).each do |source_id|
        errors << "audit event #{id} references unknown source #{source_id}" unless source_ids.include?(source_id)
      end
      Array(event["affected_nodes"]).each do |node_id|
        errors << "audit event #{id} references unknown node #{node_id}" unless node_ids.include?(node_id)
      end
    end
  end

  def validate_relations(spec, errors)
    node_ids = nodes_by_id(spec).keys.to_set
    seen = Set.new
    spec["relations"].each_with_index do |relation, index|
      %w[from to type].each do |field|
        errors << "relation #{index} missing #{field}" if blank?(relation[field])
      end
      errors << "relation #{index} unknown from #{relation['from']}" unless node_ids.include?(relation["from"])
      errors << "relation #{index} unknown to #{relation['to']}" unless node_ids.include?(relation["to"])
      signature = [relation["from"], relation["to"], relation["type"]]
      errors << "duplicate relation #{signature.join(' -> ')}" if seen.include?(signature)
      seen << signature
    end
  end

  def validate_acceptance_definitions(spec, errors)
    supported = %w[
      exact_kind_ids node_exists path_exists all_kind_have_fields
      all_kind_field_equals all_nodes_have_provenance field_equals collection_contains
    ].to_set
    spec["acceptance_tests"].each do |test|
      id = test["id"] || "<missing>"
      %w[id title rationale assertions].each do |field|
        errors << "acceptance test #{id} missing #{field}" if blank?(test[field])
      end
      Array(test["assertions"]).each do |assertion|
        errors << "acceptance test #{id} has unsupported assertion #{assertion['type']}" unless supported.include?(assertion["type"])
      end
    end
  end

  def validate_views(spec, errors)
    paths = spec["deterministic_views"].map { |view| view["path"] }
    paths.tally.select { |_path, count| count > 1 }.each_key do |path|
      errors << "duplicate deterministic view path #{path}"
    end
    spec["deterministic_views"].each do |view|
      %w[id path purpose].each do |field|
        errors << "view #{view['id']} missing #{field}" if blank?(view[field])
      end
      unless view["path"].start_with?("generated/")
        errors << "view #{view['id']} must write under generated/"
      end
    end
  end

  def validate_cycles(spec, errors)
    adjacency = graph(spec)
    state = Hash.new(:unvisited)
    visit = lambda do |node, stack|
      return if state[node] == :done
      if state[node] == :visiting
        start = stack.index(node) || 0
        errors << "dependency cycle: #{(stack[start..] + [node]).join(' -> ')}"
        return
      end

      state[node] = :visiting
      adjacency[node].each { |neighbor| visit.call(neighbor, stack + [node]) }
      state[node] = :done
    end
    nodes_by_id(spec).each_key { |node| visit.call(node, []) if state[node] == :unvisited }
  end

  def blank?(value)
    value.nil? || (value.respond_to?(:empty?) && value.empty?)
  end

  def evaluate_acceptance(spec)
    nodes = nodes_by_id(spec)
    spec["acceptance_tests"].map do |test|
      failures = Array(test["assertions"]).filter_map do |assertion|
        evaluate_assertion(spec, nodes, assertion)
      end
      { "id" => test["id"], "title" => test["title"], "passed" => failures.empty?, "failures" => failures }
    end
  end

  def evaluate_assertion(spec, nodes, assertion)
    type = assertion["type"]
    case type
    when "exact_kind_ids"
      actual = nodes.values.select { |node| node["kind"] == assertion["kind"] }.map { |node| node["id"] }.sort
      expected = assertion["ids"].sort
      "expected #{assertion['kind']} ids #{expected.inspect}, got #{actual.inspect}" unless actual == expected
    when "node_exists"
      node = nodes[assertion["id"]]
      "missing #{assertion['id']} as #{assertion['kind']}" unless node && node["kind"] == assertion["kind"]
    when "path_exists"
      "no dependency path #{assertion['from']} -> #{assertion['to']}" unless path_exists?(spec, assertion["from"], assertion["to"])
    when "all_kind_have_fields"
      missing = nodes.values.select { |node| node["kind"] == assertion["kind"] }.filter_map do |node|
        absent = assertion["fields"].select { |field| blank?(node[field]) }
        "#{node['id']}:#{absent.join(',')}" unless absent.empty?
      end
      "missing fields #{missing.join('; ')}" unless missing.empty?
    when "all_kind_field_equals"
      wrong = nodes.values.select { |node| node["kind"] == assertion["kind"] && node[assertion["field"]] != assertion["value"] }
      "#{assertion['field']} differs for #{wrong.map { |node| node['id'] }.join(', ')}" unless wrong.empty?
    when "all_nodes_have_provenance"
      wrong = nodes.values.select do |node|
        provenance = node["provenance"] || {}
        %w[origin sources ai_roles author_status].any? { |field| blank?(provenance[field]) }
      end
      "incomplete provenance for #{wrong.map { |node| node['id'] }.join(', ')}" unless wrong.empty?
    when "field_equals"
      actual = value_at_path(spec, assertion["path"])
      "#{assertion['path']} expected #{assertion['value'].inspect}, got #{actual.inspect}" unless actual == assertion["value"]
    when "collection_contains"
      actual = value_at_path(spec, assertion["path"])
      "#{assertion['path']} does not contain #{assertion['value'].inspect}" unless actual.respond_to?(:include?) && actual.include?(assertion["value"])
    else
      "unsupported assertion #{type}"
    end
  end

  def render_views(spec)
    results = evaluate_acceptance(spec)
    {
      "generated/canonical.json" => canonical_json(spec),
      "generated/minimal-reconstruction.md" => render_minimal(spec),
      "generated/audit-trail.md" => render_audit(spec),
      "generated/dependency-graph.mmd" => render_graph(spec),
      "generated/claims.csv" => render_claims(spec),
      "generated/acceptance-matrix.md" => render_acceptance(spec, results),
      "generated/rendering-review-checklist.md" => render_review_checklist(spec)
    }
  end

  def render_minimal(spec)
    kernels = spec["nodes"].select { |node| node["kind"] == "kernel" }.sort_by { |node| node["id"] }
    lines = [
      "# #{spec.dig('specification', 'title')}: minimal reconstruction",
      "",
      "Generated deterministically from `spec/ai-pacing.yaml`.",
      "",
      "Semantic SHA-256: `#{semantic_digest(spec)}`",
      "",
      spec.dig("specification", "purpose"),
      "",
      "## Kernel"
    ]
    kernels.each { |node| lines += ["", "### #{node['id']} — #{node['title']}", "", node["statement"]] }
    lines += [
      "",
      "## Reconstruction rule",
      "",
      "A work that silently contradicts, upgrades, or omits a kernel proposition is not a complete faithful reconstruction. A scoped rendering may omit claims when it declares its scope and omissions.",
      ""
    ]
    lines.join("\n")
  end

  def render_audit(spec)
    lines = [
      "# AI Pacing audit trail",
      "",
      "Generated deterministically from proposition-level provenance in `spec/ai-pacing.yaml`.",
      "",
      "| Timestamp | Phase | Event | Evidence | Nodes | Confidence |",
      "|---|---|---|---|---|---|"
    ]
    spec["audit_events"].sort_by { |event| [event["date"].to_s, event["time"].to_s, event["id"]] }.each do |event|
      summary = event["summary"].gsub("|", "\\|")
      evidence = event["evidence"].join(", ")
      nodes = event["affected_nodes"].join(", ")
      timestamp = [event["date"], event["time"]].compact.join(" ")
      lines << "| #{timestamp} | #{event['phase']} | #{summary} | #{evidence} | #{nodes} | #{event['confidence']} |"
      lines << "|  |  | Caveat: #{event['caveat'].gsub('|', '\\|')} |  |  |  |" if event["caveat"]
    end
    lines << ""
    lines.join("\n")
  end

  def render_graph(spec)
    nodes = nodes_by_id(spec)
    lines = ["flowchart LR"]
    nodes.values.sort_by { |node| node["id"] }.each do |node|
      label = "#{node['id']} — #{node['title']}".gsub('"', "'")
      lines << %(  #{node['id']}["#{label}"])
    end
    spec["relations"].sort_by { |relation| [relation["from"], relation["to"], relation["type"]] }.each do |relation|
      lines << "  #{relation['from']} -->|#{relation['type']}| #{relation['to']}"
    end
    lines << ""
    lines.join("\n")
  end

  def render_claims(spec)
    CSV.generate(row_sep: "\n") do |csv|
      csv << %w[id kind title statement origin author_status sources direct_dependents]
      adjacency = graph(spec)
      spec["nodes"].sort_by { |node| node["id"] }.each do |node|
        csv << [
          node["id"], node["kind"], node["title"], node["statement"],
          node.dig("provenance", "origin"), node.dig("provenance", "author_status"),
          Array(node.dig("provenance", "sources")).join(";"), Array(adjacency[node["id"]]).join(";")
        ]
      end
    end
  end

  def render_acceptance(spec, results)
    lines = [
      "# AI Pacing acceptance matrix",
      "",
      "Generated deterministically from executable assertions in `spec/ai-pacing.yaml`.",
      "",
      "| Test | Purpose | Result |",
      "|---|---|---|"
    ]
    tests = spec["acceptance_tests"].to_h { |test| [test["id"], test] }
    results.each do |result|
      status = result["passed"] ? "PASS" : "FAIL: #{result['failures'].join('; ')}"
      lines << "| #{result['id']} — #{result['title']} | #{tests[result['id']]['rationale'].gsub('|', '\\|')} | #{status.gsub('|', '\\|')} |"
    end
    lines += ["", "Overall: **#{results.all? { |result| result['passed'] } ? 'PASS' : 'FAIL'}**", ""]
    lines.join("\n")
  end

  def render_review_checklist(spec)
    kernel_ids = spec["nodes"].select { |node| node["kind"] == "kernel" }.map { |node| node["id"] }.sort
    policy = spec.dig("publication", "verification_policy")
    lines = [
      "# Rendering verification checklist",
      "",
      "Verification describes fidelity and the declared relationship to an exact specification state. It is not endorsement or a quality award.",
      "",
      "## Immutable targets",
      "",
      "- [ ] Record the full Git commit object ID; do not attest only to `main`, a tag, or a website URL.",
      "- [ ] Record the artifact URI and content digest.",
      "- [ ] Record the verification-policy version and evidence digest.",
      "- [ ] Identify an attributable verifier and preserve the verifier's work.",
      "",
      "## Declared relationship",
      "",
      "- [ ] Confirm the creator declared scope, omissions, interpretations, and deviations.",
      "- [ ] Treat every external artifact as a generic `rendering`; do not infer fidelity from its medium.",
      "- [ ] Resolve every covered claim ID against the targeted commit.",
      "",
      "## Kernel review"
    ]
    kernel_ids.each { |id| lines << "- [ ] #{id} is faithfully represented, explicitly out of scope, or listed as a deviation." }
    lines += [
      "",
      "## Type integrity",
      "",
      "- [ ] Hypotheses remain uncertain and retain their falsifiers.",
      "- [ ] Implementation choices are not presented as necessary kernel claims.",
      "- [ ] Open questions are not silently answered.",
      "- [ ] Criticism is judged for accurate targeting, not agreement with the specification.",
      "",
      "## Judgment",
      ""
    ]
    policy["outcomes"].each { |outcome| lines << "- [ ] `#{outcome}`" }
    lines << ""
    lines.join("\n")
  end

  def write_views(spec)
    render_views(spec).each do |relative_path, content|
      path = File.join(ROOT, relative_path)
      FileUtils.mkdir_p(File.dirname(path))
      File.write(path, content)
    end
  end

  def stale_views(spec)
    render_views(spec).filter_map do |relative_path, expected|
      path = File.join(ROOT, relative_path)
      if !File.exist?(path)
        "missing #{relative_path}"
      elsif File.read(path) != expected
        "stale #{relative_path}"
      end
    end
  end

  def transitive_impact(spec, start)
    adjacency = graph(spec)
    visited = Set.new
    queue = Array(adjacency[start])
    until queue.empty?
      node = queue.shift
      next if visited.include?(node)

      visited << node
      queue.concat(adjacency[node])
    end
    visited.to_a.sort
  end
end

if $PROGRAM_NAME == __FILE__
  command = ARGV.shift || "check"
  path = ARGV.first&.end_with?(".yaml") ? ARGV.shift : AIPacing::DEFAULT_SPEC
  begin
    spec = AIPacing.load_spec(path)
  rescue StandardError => e
    warn e.message
    exit 1
  end

  case command
  when "validate"
    errors = AIPacing.validate(spec)
    if errors.empty?
      puts "PASS structural validation"
    else
      errors.each { |error| warn "FAIL #{error}" }
      exit 1
    end
  when "accept"
    errors = AIPacing.validate(spec)
    unless errors.empty?
      errors.each { |error| warn "FAIL #{error}" }
      exit 1
    end
    results = AIPacing.evaluate_acceptance(spec)
    results.each do |result|
      puts "#{result['passed'] ? 'PASS' : 'FAIL'} #{result['id']} #{result['title']}"
      result["failures"].each { |failure| warn "  #{failure}" }
    end
    exit 1 unless results.all? { |result| result["passed"] }
  when "generate"
    errors = AIPacing.validate(spec)
    unless errors.empty?
      errors.each { |error| warn "FAIL #{error}" }
      exit 1
    end
    AIPacing.write_views(spec)
    puts "Generated #{AIPacing.render_views(spec).length} deterministic views"
    puts "Semantic SHA-256 #{AIPacing.semantic_digest(spec)}"
  when "digest"
    puts AIPacing.semantic_digest(spec)
  when "impact"
    node_id = ARGV.shift
    unless AIPacing.nodes_by_id(spec).key?(node_id)
      warn "unknown node #{node_id.inspect}"
      exit 1
    end
    puts ([node_id] + AIPacing.transitive_impact(spec, node_id)).join("\n")
  when "check"
    errors = AIPacing.validate(spec)
    results = errors.empty? ? AIPacing.evaluate_acceptance(spec) : []
    stale = errors.empty? ? AIPacing.stale_views(spec) : []
    errors.each { |error| warn "FAIL #{error}" }
    results.reject { |result| result["passed"] }.each do |result|
      result["failures"].each { |failure| warn "FAIL #{result['id']} #{failure}" }
    end
    stale.each { |failure| warn "FAIL #{failure}" }
    if errors.empty? && results.all? { |result| result["passed"] } && stale.empty?
      puts "PASS structural validation"
      puts "PASS #{results.length} semantic acceptance tests"
      puts "PASS #{AIPacing.render_views(spec).length} deterministic views are current"
      puts "Semantic SHA-256 #{AIPacing.semantic_digest(spec)}"
    else
      exit 1
    end
  else
    warn "usage: ruby tools/spec_tool.rb [validate|accept|generate|digest|impact NODE|check] [spec.yaml]"
    exit 2
  end
end
