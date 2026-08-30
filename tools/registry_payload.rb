#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "open3"
require "yaml"

module RegistryPayload
  ROOT = File.expand_path("..", __dir__)
  REPOSITORY = "https://github.com/uncomposed/ai-pacing.git"

  module_function

  def git(*args)
    output, status = Open3.capture2e("git", "-C", ROOT, *args)
    raise "git #{args.join(' ')} failed: #{output}" unless status.success?

    output.strip
  end

  def idea(commit = git("rev-parse", "HEAD"))
    {
      "slug" => "ai-pacing",
      "name" => "AI Pacing",
      "summary" => "A domestic-first regime for slowing and conditioning the conversion of frontier AI capability into irreversible power while preserving bounded research and warning time.",
      "repository" => REPOSITORY,
      "git_commit" => {"algorithm" => "sha1", "value" => commit},
      "spec_yaml" => File.read(File.join(ROOT, "spec", "ai-pacing.yaml"))
    }
  end

  def dependency_map
    envelope = YAML.safe_load(File.read(File.join(ROOT, "examples", "renderings", "dependency-map.yaml")), aliases: false).fetch("rendering")
    {
      "idea_slug" => "ai-pacing",
      "title" => "AI Pacing dependency map",
      "description" => envelope.dig("relationship", "declared_omissions").join(" "),
      "artifact" => {
        "uri" => envelope.fetch("artifact_uri"),
        "digest" => envelope.fetch("artifact_digest")
      },
      "target" => {
        "repository" => REPOSITORY,
        "object_format" => envelope.dig("renders", "git_object_format"),
        "revision" => envelope.dig("renders", "git_commit")
      },
      "creator" => envelope.fetch("creator")
    }
  end
end

if $PROGRAM_NAME == __FILE__
  payload = case ARGV.first || "idea"
            when "idea" then RegistryPayload.idea
            when "dependency-map" then RegistryPayload.dependency_map
            else
              warn "usage: ruby tools/registry_payload.rb [idea|dependency-map]"
              exit 2
            end
  puts JSON.pretty_generate(payload)
end
