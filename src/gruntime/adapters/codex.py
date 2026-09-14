"""Codex JSON event adapter. Only a terminal agent-message envelope counts."""
from ..contracts import require
from ..worker_protocol import strict_json
from .journaled_worker import JournaledWorkerProvider


class CodexProvider(JournaledWorkerProvider):
    provider_id = 'codex'

    def argv(self, request):
        return ('exec', '--json', '--ephemeral', '--ignore-user-config', '--ignore-rules',
            '--sandbox', 'read-only', '--skip-git-repo-check', '--output-schema', '/result.schema.json', '-c', 'features.shell_tool=false',
            '-c', 'web_search="disabled"', '-')

    def unwrap(self, data):
        events = [strict_json(line) for line in data.splitlines() if line.strip()]
        require(bool(events) and events[-1].get('type') == 'turn.completed'
                and not any(e.get('type') in ('error', 'turn.failed') for e in events),
                'no successful structured terminal event')  # guard:gr07_codex_terminal
        messages = [e['item']['text'] for e in events if e.get('type') == 'item.completed'
            and e.get('item', {}).get('type') == 'agent_message']
        require(len(messages) == 1, 'ambiguous final result')  # guard:gr07_codex_message
        return messages[0].encode('utf-8')
