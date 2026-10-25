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
  DEFAULT_REGISTRY = File.join(ROOT, "spec", "id-registry.yaml")
  EDITORIAL_REFERENCE = File.join(ROOT, "AI_Pacing_Canonical_Spec_v0.1.md")
  # Statuses the canonical editor has given. "unresolved" marks an open question
  # the editor accepted as a question; it is accepted canon, not a proposal.
  ACCEPTED_STATUSES = %w[
    accepted accepted-after-revision accepted-after-wording-correction
    accepted-as-hypothesis accepted-as-option unresolved
  ].freeze
  # A proposed node is recorded in the YAML for review but is not accepted canon.
  PROPOSED_STATUS = "proposed"
  AUTHOR_STATUSES = (ACCEPTED_STATUSES + [PROPOSED_STATUS]).freeze
  KIND_PREFIXES = {
    "kernel" => "K", "derived" => "D", "hypothesis" => "H",
    "implementation" => "I", "open_question" => "Q"
  }.freeze
  # IDs whose YAML and editorial-reference meanings already differed when the
  # registry was created (the 2026-08-29 conformance gap). No other ID may be
  # registered as a legacy collision.
  LEGACY_COLLISION_IDS = %w[D1 D2 D3 D4 D5 D6 H1 H2 H3 H4 H5 I1 I2 I3 Q3 Q4].freeze
  REGISTRY_COLLISIONS = %w[none same-proposition legacy reserved-conflict].freeze
  REGISTRY_STATUSES = {
    "yaml" => %w[accepted proposed],
    "editorial" => %w[editorial]
  }.freeze

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

  def proposed?(node)
    node.is_a?(Hash) && node.dig("provenance", "author_status") == PROPOSED_STATUS
  end

  def accepted?(node)
    !proposed?(node)
  end

  def accepted_kernel_ids(spec)
    Array(spec["nodes"]).select { |node| node["kind"] == "kernel" && accepted?(node) }.map { |node| node["id"] }.sort
  end

  def proposed_ids(spec)
    Array(spec["nodes"]).select { |node| proposed?(node) }.map { |node| node["id"] }.sort
  end

  # The accepted canon: proposed nodes and every relation touching one removed.
  # Identity and dependency-path acceptance assertions run against this view.
  def accepted_spec(spec)
    proposed = proposed_ids(spec).to_set
    canon = spec.dup
    canon["nodes"] = Array(spec["nodes"]).reject { |node| proposed.include?(node["id"]) }
    canon["relations"] = Array(spec["relations"]).reject do |relation|
      proposed.include?(relation["from"]) || proposed.include?(relation["to"])
    end
    canon
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
      status = provenance["author_status"]
      if !blank?(status) && !AUTHOR_STATUSES.include?(status)
        errors << "node #{id} has unknown author_status #{status.inspect}"
      end
      if proposed?(node)
        proposal = node["proposal"]
        if !proposal.is_a?(Hash) || blank?(proposal["issue"])
          errors << "proposed node #{id} must name its proposal issue"
        end
      end
      Array(provenance["sources"]).each do |source_id|
        errors << "node #{id} references unknown source #{source_id}" unless source_ids.include?(source_id)
      end

      NODE_REFERENCE_FIELDS.each do |field|
        Array(node[field]).each do |target|
          errors << "node #{id} #{field} references unknown node #{target}" unless node_ids.include?(target)
          if accepted?(node) && proposed?(nodes_by_id(spec)[target])
            errors << "accepted node #{id} #{field} references proposed node #{target}"
          end
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
      from_node = nodes_by_id(spec)[relation["from"]]
      to_node = nodes_by_id(spec)[relation["to"]]
      if %w[grounds implements].include?(relation["type"]) && proposed?(from_node) && to_node && accepted?(to_node)
        errors << "accepted node #{relation['to']} cannot be #{relation['type'] == 'grounds' ? 'grounded' : 'implemented'} by proposed node #{relation['from']}"
      end
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

  # Identity assertions (exact_kind_ids, node_exists, path_exists) see only the
  # accepted canon, so a proposed node can neither satisfy nor break them.
  # Field assertions apply to every node, proposed ones included.
  def evaluate_acceptance(spec)
    canon = accepted_spec(spec)
    spec["acceptance_tests"].map do |test|
      failures = Array(test["assertions"]).filter_map do |assertion|
        evaluate_assertion(spec, canon, assertion)
      end
      { "id" => test["id"], "title" => test["title"], "passed" => failures.empty?, "failures" => failures }
    end
  end

  def evaluate_assertion(spec, canon, assertion)
    nodes = nodes_by_id(spec)
    accepted_nodes = nodes_by_id(canon)
    type = assertion["type"]
    case type
    when "exact_kind_ids"
      actual = accepted_nodes.values.select { |node| node["kind"] == assertion["kind"] }.map { |node| node["id"] }.sort
      expected = assertion["ids"].sort
      "expected #{assertion['kind']} ids #{expected.inspect}, got #{actual.inspect}" unless actual == expected
    when "node_exists"
      node = accepted_nodes[assertion["id"]]
      "missing accepted #{assertion['id']} as #{assertion['kind']}" unless node && node["kind"] == assertion["kind"]
    when "path_exists"
      unless accepted_nodes.key?(assertion["from"]) && accepted_nodes.key?(assertion["to"]) &&
             path_exists?(canon, assertion["from"], assertion["to"])
        "no accepted dependency path #{assertion['from']} -> #{assertion['to']}"
      end
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
    kernels = spec["nodes"].select { |node| node["kind"] == "kernel" && accepted?(node) }.sort_by { |node| node["id"] }
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
    proposed = proposed_ids(spec)
    unless proposed.empty?
      lines << "  classDef proposed stroke-dasharray: 5 5"
      lines << "  class #{proposed.join(',')} proposed"
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
    proposed = proposed_ids(spec)
    unless proposed.empty?
      lines += [
        "Proposed nodes, not accepted by the canonical editor: #{proposed.join(', ')}. " \
        "They are excluded from kernel-identity, node-existence, and dependency-path assertions " \
        "and are still subject to field assertions.",
        ""
      ]
    end
    lines.join("\n")
  end

  def render_review_checklist(spec)
    kernel_ids = accepted_kernel_ids(spec)
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
      "- [ ] Proposed nodes (`author_status: proposed`) are not presented as accepted canon.",
      "- [ ] Criticism is judged for accurate targeting, not agreement with the specification.",
      "",
      "## Judgment",
      ""
    ]
    policy["outcomes"].each { |outcome| lines << "- [ ] `#{outcome}`" }
    lines << ""
    lines.join("\n")
  end

  def load_registry(path = DEFAULT_REGISTRY)
    YAML.safe_load(File.read(path), permitted_classes: [Date], aliases: false)
  rescue Errno::ENOENT
    raise ArgumentError, "missing reserved-ID registry #{path}"
  rescue Psych::Exception => e
    raise ArgumentError, "registry YAML parse error: #{e.message}"
  end

  def id_number(id)
    id.to_s[1..].to_i
  end

  def editorial_headings(path = EDITORIAL_REFERENCE)
    return {} unless File.exist?(path)

    File.foreach(path).each_with_object({}) do |line, headings|
      match = line.match(/^## ([KDIHQ]\d+) — (.+?)\s*$/)
      headings[match[1]] = match[2] if match
    end
  end

  # Enforces spec/id-registry.yaml: every YAML node ID is registered and unique
  # across the YAML, the editorial reference, and reserved research/issue IDs.
  def validate_registry(spec, registry, editorial_path = EDITORIAL_REFERENCE)
    errors = []
    return ["registry root must be a mapping"] unless registry.is_a?(Hash)

    sources = registry["sources"]
    entries = registry["ids"]
    return ["registry missing sources"] unless sources.is_a?(Hash) && !sources.empty?
    return ["registry missing ids"] unless entries.is_a?(Array)

    entries.map { |entry| entry["id"] }.tally.select { |_id, count| count > 1 }.each_key do |id|
      errors << "registry: duplicate entry #{id}"
    end
    by_id = entries.to_h { |entry| [entry["id"], entry] }

    entries.each do |entry|
      id = entry["id"].to_s
      kind = entry["kind"]
      prefix = KIND_PREFIXES[kind]
      if prefix.nil?
        errors << "registry: #{id} has unknown kind #{kind.inspect}"
      elsif !id.match?(/\A#{prefix}[1-9]\d*\z/)
        errors << "registry: #{id} does not use #{kind} prefix #{prefix}"
      end
      definitions = Array(entry["definitions"])
      errors << "registry: #{id} has no definitions" if definitions.empty?
      definitions.each do |definition|
        source = definition["source"]
        status = definition["status"]
        if !sources.key?(source)
          errors << "registry: #{id} cites undeclared source #{source.inspect}"
        elsif !REGISTRY_STATUSES.fetch(source, %w[reserved]).include?(status)
          errors << "registry: #{id} #{source} definition has invalid status #{status.inspect}"
        end
        errors << "registry: #{id} #{source} definition missing title" if blank?(definition["title"])
      end
      errors << "registry: #{id} defined twice by #{definitions.map { |d| d['source'] }.tally.select { |_s, c| c > 1 }.keys.join(', ')}" if definitions.map { |d| d["source"] }.uniq.length != definitions.length

      collision = entry["collision"]
      if !REGISTRY_COLLISIONS.include?(collision)
        errors << "registry: #{id} has invalid collision #{collision.inspect}"
      elsif definitions.length <= 1 && collision != "none"
        errors << "registry: #{id} has one definition but collision #{collision}"
      elsif definitions.length > 1 && collision == "none"
        errors << "registry: #{id} has #{definitions.length} definitions; declare same-proposition, legacy, or reserved-conflict"
      end
      yaml_definition = definitions.find { |d| d["source"] == "yaml" }
      if collision == "legacy" && !LEGACY_COLLISION_IDS.include?(id)
        errors << "registry: #{id} cannot be a legacy collision; only the 2026-08-29 conformance gap is grandfathered"
      end
      if collision == "reserved-conflict" && yaml_definition
        errors << "registry: #{id} is a reserved conflict and cannot be used in the YAML"
      end
      if collision == "legacy" && !yaml_definition
        errors << "registry: legacy collision #{id} has no YAML definition"
      end
      if yaml_definition && yaml_definition["status"] == "proposed" && collision != "none" && collision != "same-proposition"
        errors << "registry: proposed YAML node #{id} must not collide with another definition"
      end
    end

    nodes = nodes_by_id(spec)
    nodes.each_value do |node|
      id = node["id"]
      entry = by_id[id]
      definition = entry && Array(entry["definitions"]).find { |d| d["source"] == "yaml" }
      if definition.nil?
        errors << "registry: YAML node #{id} is not registered with a yaml definition"
        next
      end
      errors << "registry: #{id} kind #{entry['kind']} differs from YAML kind #{node['kind']}" if entry["kind"] != node["kind"]
      errors << "registry: #{id} yaml title differs from YAML node title" if definition["title"] != node["title"]
      expected = proposed?(node) ? "proposed" : "accepted"
      errors << "registry: #{id} yaml status #{definition['status']} differs from YAML (#{expected})" if definition["status"] != expected
    end
    entries.each do |entry|
      next unless Array(entry["definitions"]).any? { |d| d["source"] == "yaml" }

      errors << "registry: #{entry['id']} has a yaml definition but no YAML node" unless nodes.key?(entry["id"])
    end

    editorial_headings(editorial_path).each do |id, title|
      definition = by_id[id] && Array(by_id[id]["definitions"]).find { |d| d["source"] == "editorial" }
      if definition.nil?
        errors << "registry: editorial reference ID #{id} is not registered"
      elsif definition["title"] != title
        errors << "registry: #{id} editorial title differs from the editorial reference"
      end
    end

    local_ids = Array(registry["local_namespaces"]).flat_map { |namespace| Array(namespace["ids"]) }
    next_free = registry["next_free"] || {}
    KIND_PREFIXES.each do |kind, prefix|
      candidate = next_free[prefix]
      if candidate.nil? || !candidate.to_s.match?(/\A#{prefix}[1-9]\d*\z/)
        errors << "registry: next_free #{prefix} missing or malformed"
        next
      end
      used = entries.select { |entry| entry["kind"] == kind }.map { |entry| id_number(entry["id"]) }
      used += local_ids.select { |id| id.to_s.start_with?(prefix) }.map { |id| id_number(id) }
      if used.any? && id_number(candidate) <= used.max
        errors << "registry: next_free #{candidate} is not above every used or reserved #{prefix} ID"
      end
    end

    Array(registry["renumbering"]).each do |mapping|
      errors << "registry: renumbering #{mapping['old']} cites undeclared source #{mapping['source'].inspect}" unless sources.key?(mapping["source"])
      errors << "registry: renumbering target #{mapping['new']} is not registered" unless by_id.key?(mapping["new"])
      if mapping["old"].to_s[0] != mapping["new"].to_s[0]
        errors << "registry: renumbering #{mapping['old']} -> #{mapping['new']} changes kind"
      end
    end
    errors
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
    begin
      errors += AIPacing.validate_registry(spec, AIPacing.load_registry)
    rescue ArgumentError => e
      errors << e.message
    end
    results = errors.empty? ? AIPacing.evaluate_acceptance(spec) : []
    stale = errors.empty? ? AIPacing.stale_views(spec) : []
    errors.each { |error| warn "FAIL #{error}" }
    results.reject { |result| result["passed"] }.each do |result|
      result["failures"].each { |failure| warn "FAIL #{result['id']} #{failure}" }
    end
    stale.each { |failure| warn "FAIL #{failure}" }
    if errors.empty? && results.all? { |result| result["passed"] } && stale.empty?
      puts "PASS structural validation"
      puts "PASS reserved-ID registry"
      puts "PASS #{results.length} semantic acceptance tests"
      puts "PASS #{AIPacing.render_views(spec).length} deterministic views are current"
      puts "Semantic SHA-256 #{AIPacing.semantic_digest(spec)}"
    else
      exit 1
    end
  when "next-id"
    prefix = ARGV.shift.to_s.upcase
    unless AIPacing::KIND_PREFIXES.value?(prefix)
      warn "usage: ruby tools/spec_tool.rb next-id K|D|H|I|Q"
      exit 2
    end
    puts AIPacing.load_registry.fetch("next_free").fetch(prefix)
  else
    warn "usage: ruby tools/spec_tool.rb [validate|accept|generate|digest|impact NODE|next-id PREFIX|check] [spec.yaml]"
    exit 2
  end
end
