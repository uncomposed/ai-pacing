#!/usr/bin/env ruby
# frozen_string_literal: true

require "digest"
require "open3"
require_relative "spec_tool"

module AIPacingRendering
  RELATIONSHIPS = %w[faithful scoped critique variant].freeze
  REQUESTED_JUDGMENTS = %w[verified verified_with_deviations].freeze

  module_function

  def load_manifest(path)
    YAML.safe_load(File.read(path), permitted_classes: [Date], aliases: false)
  rescue Psych::Exception => e
    raise ArgumentError, "rendering YAML parse error: #{e.message}"
  end

  def git(*arguments)
    stdout, stderr, status = Open3.capture3("git", *arguments, chdir: AIPacing::ROOT)
    [stdout, stderr, status.success?]
  end

  def target_spec(manifest)
    rendering = manifest.fetch("rendering")
    target = rendering.fetch("renders")
    commit = target.fetch("git_commit")
    spec_path = target.fetch("spec_path")
    contents, stderr, success = git("show", "#{commit}:#{spec_path}")
    raise ArgumentError, "cannot load targeted specification: #{stderr.strip}" unless success

    YAML.safe_load(contents, permitted_classes: [Date], aliases: false)
  rescue KeyError => e
    raise ArgumentError, "missing rendering target field: #{e.message}"
  end

  def validate(manifest, verify_git: true)
    errors = []
    unless manifest.is_a?(Hash)
      return ["root must be a mapping"]
    end
    errors << "rendering_version must equal 1" unless manifest["rendering_version"] == 1
    rendering = manifest["rendering"]
    return errors << "missing rendering" unless rendering.is_a?(Hash)

    %w[id artifact_uri artifact_digest creator renders relationship verifier_request].each do |field|
      errors << "rendering missing #{field}" if AIPacing.blank?(rendering[field])
    end
    return errors unless errors.empty?

    errors << "creator must contain id" if AIPacing.blank?(rendering.dig("creator", "id"))
    digest = rendering["artifact_digest"]
    errors << "artifact_digest must be sha256:<64 lowercase hex>" unless digest.match?(/\Asha256:[0-9a-f]{64}\z/)

    target = rendering["renders"]
    %w[idea git_object_format git_commit spec_path].each do |field|
      errors << "renders missing #{field}" if AIPacing.blank?(target[field])
    end
    commit = target["git_commit"].to_s
    format = target["git_object_format"]
    expected_length = {"sha1" => 40, "sha256" => 64}[format]
    if expected_length.nil?
      errors << "git_object_format must be sha1 or sha256"
    elsif !commit.match?(/\A[0-9a-f]{#{expected_length}}\z/)
      errors << "git_commit must be a full #{expected_length}-hex #{format} object ID"
    end

    relationship = rendering["relationship"]
    %w[claim covers declared_omissions declared_deviations].each do |field|
      errors << "relationship missing #{field}" unless relationship.key?(field)
    end
    errors << "unknown relationship claim #{relationship['claim'].inspect}" unless RELATIONSHIPS.include?(relationship["claim"])
    errors << "covers must not contain duplicates" unless Array(relationship["covers"]).uniq.length == Array(relationship["covers"]).length

    request = rendering["verifier_request"]
    errors << "verifier_request missing policy_version" if AIPacing.blank?(request["policy_version"])
    unless REQUESTED_JUDGMENTS.include?(request["requested_judgment"])
      errors << "unknown requested_judgment #{request['requested_judgment'].inspect}"
    end
    return errors unless errors.empty?

    if verify_git && expected_length && commit.match?(/\A[0-9a-f]{#{expected_length}}\z/)
      resolved, stderr, success = git("rev-parse", "#{commit}^{commit}")
      if !success
        errors << "target commit does not resolve locally: #{stderr.strip}"
      elsif resolved.strip != commit
        errors << "target is not the resolved full commit object ID"
      else
        begin
          spec = target_spec(manifest)
          spec_errors = AIPacing.validate(spec)
          errors.concat(spec_errors.map { |error| "target spec invalid: #{error}" })
          if spec_errors.empty?
            nodes = AIPacing.nodes_by_id(spec)
            Array(relationship["covers"]).each do |node_id|
              errors << "covers unknown target node #{node_id}" unless nodes.key?(node_id)
            end
            if relationship["claim"] == "faithful"
              kernel_ids = nodes.values.select { |node| node["kind"] == "kernel" }.map { |node| node["id"] }.sort
              missing = kernel_ids - Array(relationship["covers"])
              errors << "faithful rendering does not cover kernel nodes #{missing.join(', ')}" unless missing.empty?
            end
          end
        rescue ArgumentError => e
          errors << e.message
        end

        artifact_path = rendering["artifact_git_path"]
        if artifact_path
          bytes, artifact_error, artifact_ok = git("show", "#{commit}:#{artifact_path}")
          if !artifact_ok
            errors << "cannot read artifact at target commit: #{artifact_error.strip}"
          else
            actual = "sha256:#{Digest::SHA256.hexdigest(bytes)}"
            errors << "artifact digest mismatch: expected #{digest}, got #{actual}" unless actual == digest
          end
        end
      end
    end
    errors
  end
end

if $PROGRAM_NAME == __FILE__
  path = ARGV.shift
  unless path
    warn "usage: ruby tools/rendering_tool.rb MANIFEST.yaml"
    exit 2
  end
  begin
    manifest = AIPacingRendering.load_manifest(path)
    errors = AIPacingRendering.validate(manifest)
  rescue StandardError => e
    warn "FAIL #{e.message}"
    exit 1
  end
  if errors.empty?
    rendering = manifest["rendering"]
    puts "PASS rendering manifest"
    puts "Target #{rendering.dig('renders', 'git_commit')}"
    puts "Artifact #{rendering['artifact_digest']}"
    puts "Relationship #{rendering.dig('relationship', 'claim')}"
  else
    errors.each { |error| warn "FAIL #{error}" }
    exit 1
  end
end
