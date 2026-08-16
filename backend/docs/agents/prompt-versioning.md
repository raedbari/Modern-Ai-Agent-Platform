# Prompt versioning foundation

Sprint 1 uses an immutable version identifier on each Agent rather than a
prompt CMS. `Agent.prompt_version` defaults to `v1`; changing prompt content in
an operational workflow requires assigning a new non-empty version identifier.

The trusted chat context copies `prompt_version` into `RuntimeContext`. The
generation request telemetry and persisted assistant-message metadata therefore
identify the prompt version used for a turn. Evaluation run configuration also
records dataset, agent, prompt, knowledge, provider, and model versions.

Historical prompt bodies and activation workflows are deliberately deferred.
Until those exist, deployment/change management must retain the prompt text
associated with each version. Evaluation comparisons must never reuse a prompt
version label for different content.
