---
name: preflight-inline
description: Review inline skill snapshots only
tools: [finish]
excludeDefaultComponents: true
mainAgent: true
subagent: false
model: inherit
commandExecutionPolicy: 'off'
mcpServers: []
skills: []
plugins: []
---
Inspect only inline snapshots. No filesystem inspection, operational tools or delegation. Return a cited Markdown report; native completion machinery only.
