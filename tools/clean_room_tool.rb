#!/usr/bin/env ruby
# frozen_string_literal: true

require "digest"
require "fileutils"
require "json"
require "tmpdir"
require "yaml"
require_relative "spec_tool"

module CleanRoom
  ROOT = File.expand_path("..", __dir__)
  DEFAULT_OUTPUT = File.join(ROOT, "build", "clean-room-generator")
  SOURCE_SPEC = File.join(ROOT, "spec", "ai-pacing.yaml")
  TASK = File.join(ROOT, "eval", "clean-room", "generator-task.md")
  COVERAGE_SCHEMA = File.join(ROOT, "eval", "clean-room", "coverage.schema.json")
  EDITORIAL_REFERENCE = File.join(ROOT, "AI_Pacing_Canonical_Spec_v0.1.md")
  PACKET_CONTENT = {
    "source.yaml" => SOURCE_SPEC,
    "TASK.md" => TASK,
    "coverage.schema.json" => COVERAGE_SCHEMA
  }.freeze
  PACKET_FILES = (PACKET_CONTENT.keys + ["MANIFEST.json"]).sort.freeze
  FORBIDDEN_PACKET_NAMES = %w[
    AI_Pacing_Canonical_Spec_v0.1.md
    minimal-reconstruction.md
    evaluation-rubric.yaml
    README.md
  ].freeze

  module_function

  def sha256(path)
    Digest::SHA256.file(path).hexdigest
  end

  def build(output = DEFAULT_OUTPUT)
    output = File.expand_path(output)
    allowed_root = File.expand_path(File.join(ROOT, "build"))
    unless output == allowed_root || output.start_with?(allowed_root + File::SEPARATOR) || output.start_with?(Dir.tmpdir + File::SEPARATOR)
      raise ArgumentError, "output must be under #{allowed_root} or the system temporary directory"
    end

    FileUtils.mkdir_p(output)
    unexpected = Dir.children(output) - PACKET_FILES
    raise ArgumentError, "refusing to overwrite directory with unexpected files: #{unexpected.sort.join(', ')}" unless unexpected.empty?

    PACKET_CONTENT.each do |name, source|
      FileUtils.cp(source, File.join(output, name))
    end

    spec = AIPacing.load_spec(SOURCE_SPEC)
    manifest = {
      "protocol" => "clean-room-reconstruction-v0.1",
      "source_semantic_sha256" => AIPacing.semantic_digest(spec),
      "files" => PACKET_CONTENT.keys.sort.map do |name|
        {"name" => name, "sha256" => sha256(File.join(output, name))}
      end,
      "isolation_conditions" => [
        "fresh model context with no prior conversation or rendering",
        "no files outside this packet",
        "no web or retrieval access",
        "no evaluator rubric or canonical Markdown"
      ]
    }
    File.write(File.join(output, "MANIFEST.json"), JSON.pretty_generate(manifest) + "\n")
    validate_packet(output)
    manifest
  end

  def validate_packet(output)
    names = Dir.children(output).sort
    errors = []
    errors << "packet files differ: expected #{PACKET_FILES.inspect}, got #{names.inspect}" unless names == PACKET_FILES
    forbidden = names & FORBIDDEN_PACKET_NAMES
    errors << "packet contains forbidden files: #{forbidden.join(', ')}" unless forbidden.empty?

    manifest_path = File.join(output, "MANIFEST.json")
    if File.exist?(manifest_path)
      manifest = JSON.parse(File.read(manifest_path))
      Array(manifest["files"]).each do |entry|
        path = File.join(output, entry.fetch("name"))
        errors << "missing #{entry['name']}" unless File.exist?(path)
        errors << "digest mismatch for #{entry['name']}" if File.exist?(path) && sha256(path) != entry["sha256"]
      end
      spec = AIPacing.load_spec(File.join(output, "source.yaml")) if File.exist?(File.join(output, "source.yaml"))
      if spec && AIPacing.semantic_digest(spec) != manifest["source_semantic_sha256"]
        errors << "source semantic digest differs from manifest"
      end
    end
    errors
  end

  def markdown_nodes(path = EDITORIAL_REFERENCE)
    nodes = {}
    current = nil
    File.foreach(path) do |line|
      if (match = line.match(/^## ([KDIHQ]\d+) — (.+?)\s*$/))
        current = match[1]
        nodes[current] = {"id" => current, "title" => match[2], "kind" => inferred_kind(current)}
      elsif current && (match = line.match(/^\*\*Type:\*\*\s*(.+?)\s*$/))
        nodes[current]["declared_type"] = match[1]
      end
    end
    nodes
  end

  def inferred_kind(id)
    {"K" => "kernel", "D" => "derived", "H" => "hypothesis", "I" => "implementation", "Q" => "open_question"}.fetch(id[0])
  end

  def normalized_title(title)
    title.downcase.gsub(/[^a-z0-9]+/, " ").strip
  end

  def audit
    markdown = markdown_nodes
    yaml_nodes = AIPacing.nodes_by_id(AIPacing.load_spec)
    missing = markdown.keys - yaml_nodes.keys
    extra = yaml_nodes.keys - markdown.keys
    shared = markdown.keys & yaml_nodes.keys
    kind_mismatches = shared.select { |id| markdown[id]["kind"] != yaml_nodes[id]["kind"] }
    title_mismatches = shared.select do |id|
      normalized_title(markdown[id]["title"]) != normalized_title(yaml_nodes[id]["title"])
    end
    {
      "markdown_node_count" => markdown.length,
      "yaml_node_count" => yaml_nodes.length,
      "missing_from_yaml" => missing.sort,
      "extra_in_yaml" => extra.sort,
      "kind_mismatches" => kind_mismatches.sort,
      "title_mismatches" => title_mismatches.sort.map do |id|
        {"id" => id, "markdown" => markdown[id]["title"], "yaml" => yaml_nodes[id]["title"]}
      end
    }
  end

  def validate_output(output)
    output = File.expand_path(output)
    rendering_path = File.join(output, "rendering.md")
    coverage_path = File.join(output, "coverage.yaml")
    errors = []
    errors << "missing rendering.md" unless File.file?(rendering_path)
    errors << "missing coverage.yaml" unless File.file?(coverage_path)
    return errors unless errors.empty?

    word_count = File.read(rendering_path).scan(/\b[[:alnum:]'’-]+\b/).length
    errors << "rendering.md has #{word_count} words; expected 1200..1800" unless (1200..1800).cover?(word_count)

    begin
      coverage = YAML.safe_load(File.read(coverage_path), aliases: false)
    rescue Psych::Exception => e
      return errors + ["coverage.yaml parse error: #{e.message}"]
    end
    return errors + ["coverage.yaml root must be a mapping"] unless coverage.is_a?(Hash)

    required = %w[
      source_semantic_sha256 relationship_claim covered_nodes omitted_nodes
      declared_deviations added_inferences uncertainty_treatment
    ]
    required.each { |field| errors << "coverage.yaml missing #{field}" unless coverage.key?(field) }

    spec = AIPacing.load_spec
    expected_digest = AIPacing.semantic_digest(spec)
    errors << "source semantic digest mismatch" unless coverage["source_semantic_sha256"] == expected_digest
    errors << "relationship_claim must be faithful_reconstruction" unless coverage["relationship_claim"] == "faithful_reconstruction"

    all_ids = AIPacing.nodes_by_id(spec).keys
    covered = Array(coverage["covered_nodes"])
    omitted = Array(coverage["omitted_nodes"])
    covered_ids = covered.filter_map { |entry| entry["id"] if entry.is_a?(Hash) }
    omitted_ids = omitted.filter_map { |entry| entry["id"] if entry.is_a?(Hash) }
    declared_ids = covered_ids + omitted_ids
    duplicates = declared_ids.tally.select { |_id, count| count > 1 }.keys.sort
    unknown = declared_ids.uniq - all_ids
    missing = all_ids - declared_ids.uniq
    errors << "duplicate covered-or-omitted IDs: #{duplicates.join(', ')}" unless duplicates.empty?
    errors << "unknown covered-or-omitted IDs: #{unknown.sort.join(', ')}" unless unknown.empty?
    errors << "nodes neither covered nor omitted: #{missing.sort.join(', ')}" unless missing.empty?

    covered.each_with_index do |entry, index|
      next unless entry.is_a?(Hash)
      %w[id rendering_section paraphrase].each do |field|
        errors << "covered_nodes[#{index}] missing #{field}" if entry[field].to_s.strip.empty?
      end
    end
    omitted.each_with_index do |entry, index|
      next unless entry.is_a?(Hash)
      %w[id reason].each do |field|
        errors << "omitted_nodes[#{index}] missing #{field}" if entry[field].to_s.strip.empty?
      end
    end

    treatment_ids = Array(coverage["uncertainty_treatment"]).filter_map do |entry|
      entry["id"] if entry.is_a?(Hash) && !entry["treatment"].to_s.strip.empty?
    end
    covered_hypotheses = covered_ids.select { |id| AIPacing.nodes_by_id(spec).dig(id, "kind") == "hypothesis" }
    untreated = covered_hypotheses - treatment_ids
    errors << "covered hypotheses without uncertainty treatment: #{untreated.sort.join(', ')}" unless untreated.empty?

    deviation_ids = Array(coverage["declared_deviations"]).filter_map { |entry| entry["id"] if entry.is_a?(Hash) }
    unknown_deviations = deviation_ids.uniq - all_ids
    errors << "unknown deviation IDs: #{unknown_deviations.sort.join(', ')}" unless unknown_deviations.empty?
    errors
  end
end

if $PROGRAM_NAME == __FILE__
  command = ARGV.shift || "audit"
  case command
  when "build"
    output = ARGV.shift || CleanRoom::DEFAULT_OUTPUT
    manifest = CleanRoom.build(output)
    puts "PASS built isolated packet at #{output}"
    puts "Source semantic SHA-256 #{manifest['source_semantic_sha256']}"
    puts "Files: #{CleanRoom::PACKET_FILES.join(', ')}"
  when "check"
    output = ARGV.shift || CleanRoom::DEFAULT_OUTPUT
    errors = CleanRoom.validate_packet(output)
    if errors.empty?
      puts "PASS isolated packet #{output}"
    else
      errors.each { |error| warn "FAIL #{error}" }
      exit 1
    end
  when "audit"
    puts JSON.pretty_generate(CleanRoom.audit)
  when "preflight"
    output = ARGV.shift
    unless output
      warn "preflight requires a model-output directory"
      exit 2
    end
    errors = CleanRoom.validate_output(output)
    if errors.empty?
      puts "PASS model output deterministic preflight"
    else
      errors.each { |error| warn "FAIL #{error}" }
      exit 1
    end
  else
    warn "usage: ruby tools/clean_room_tool.rb [build [output]|check [output]|audit|preflight output]"
    exit 2
  end
end
