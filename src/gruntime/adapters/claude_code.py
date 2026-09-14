"""Claude Code structured result adapter; CLI prose is never a verdict."""
from ..canonical import canonical_json
from ..contracts import require
from ..worker_protocol import RESULT_SCHEMA, strict_json
from .journaled_worker import JournaledWorkerProvider


class ClaudeCodeProvider(JournaledWorkerProvider):
    provider_id = 'claude-code'
    relay_headers = ('anthropic-version', 'anthropic-beta')

    def relay_environment(self):
        # This public placeholder only selects API auth in the CLI. The relay
        # strips it; the upstream credential exists only in the kernel relay.
        return ('ANTHROPIC_BASE_URL', {'ANTHROPIC_API_KEY': 'governed-local-bridge',
            'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1'})

    def argv(self, request):
        return ('--print', '--output-format', 'json', '--json-schema', canonical_json(RESULT_SCHEMA).decode(),
            '--tools', '', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
            '--setting-sources', '', '--no-session-persistence', '--session-id', request.session_id,
            '--disable-slash-commands', '--bare')

    def unwrap(self, data):
        outer = strict_json(data)
        require(type(outer) is dict and outer.get('type') == 'result' and outer.get('subtype') == 'success'
                and outer.get('is_error') is False, 'invalid structured CLI result')  # guard:gr07_claude_result
        return canonical_json(outer['structured_output'])
