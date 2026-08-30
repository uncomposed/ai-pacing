#!/usr/bin/env ruby
# frozen_string_literal: true

require "base64"
require "yaml"

module IRAPReadiness
  ROOT = File.expand_path("..", __dir__)
  MANIFEST = File.join(ROOT, ".idea", "manifest.yaml")

  module_function

  def load_yaml(path)
    YAML.safe_load(File.read(path), aliases: false)
  rescue Psych::Exception => e
    raise ArgumentError, "#{path}: #{e.message}"
  end

  def value_at(value, path)
    path.reduce(value) { |current, key| current.is_a?(Hash) ? current[key] : nil }
  end

  def validate
    errors = []
    manifest = load_yaml(MANIFEST)
    required = [
      %w[spec_version], %w[idea id], %w[idea name],
      %w[repository object_format], %w[repository canonical_ref],
      %w[verification verifiers_path], %w[verification policy_path]
    ]
    required.each do |path|
      errors << "manifest missing #{path.join('.')}" if value_at(manifest, path).to_s.strip.empty?
    end
    errors << "object format must be sha1 or sha256" unless %w[sha1 sha256].include?(manifest.dig("repository", "object_format"))
    canonical_ref = manifest.dig("repository", "canonical_ref").to_s
    errors << "canonical_ref must be a full branch ref" unless canonical_ref.match?(%r{\Arefs/heads/[^/].+\z})

    mirrors = Array(manifest.dig("repository", "mirrors"))
    errors << "at least one HTTPS Git mirror is required for registry import" if mirrors.empty?
    mirrors.each do |mirror|
      errors << "mirror must be an HTTPS .git URL: #{mirror}" unless mirror.match?(%r{\Ahttps://.+\.git\z})
    end

    verifier_path = File.join(ROOT, manifest.dig("verification", "verifiers_path").to_s)
    policy_path = File.join(ROOT, manifest.dig("verification", "policy_path").to_s)
    errors << "missing verifier registry" unless File.file?(verifier_path)
    errors << "missing verification policy" unless File.file?(policy_path)
    return errors unless errors.empty?

    registry = load_yaml(verifier_path)
    policy = load_yaml(policy_path)
    verifiers = Array(registry["verifiers"])
    verifier_ids = verifiers.map { |verifier| verifier["id"] }
    errors << "verifier IDs must be unique and nonempty" unless verifier_ids.all? { |id| !id.to_s.empty? } && verifier_ids.uniq.length == verifier_ids.length
    verifiers.each do |verifier|
      keys = Array(verifier["keys"])
      errors << "verifier #{verifier['id']} has no key" if keys.empty?
      keys.each do |key|
        errors << "key #{key['id']} must use Ed25519" unless key["algorithm"] == "Ed25519"
        begin
          bytes = Base64.strict_decode64(key["public_key_base64"].to_s)
          errors << "key #{key['id']} must contain 32 Ed25519 public-key bytes" unless bytes.bytesize == 32
        rescue ArgumentError
          errors << "key #{key['id']} has invalid base64"
        end
      end
    end

    claims = policy["claims"] || {}
    errors << "policy must define faithful_rendering" unless claims.key?("faithful_rendering")
    claims.each do |name, claim|
      eligible = Array(claim.dig("recognition", "eligible_verifiers", "ids"))
      errors << "claim #{name} has no eligible verifier" if eligible.empty?
      (eligible - verifier_ids).each { |id| errors << "claim #{name} references unknown verifier #{id}" }
      errors << "claim #{name} must define a recognition rule" if claim.dig("recognition", "rule", "type").to_s.empty?
    end
    errors
  end
end

if $PROGRAM_NAME == __FILE__
  errors = IRAPReadiness.validate
  if errors.empty?
    puts "PASS IRAP repository metadata"
  else
    errors.each { |error| warn "FAIL #{error}" }
    exit 1
  end
end
