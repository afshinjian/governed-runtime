"""Versioned JSON wire values. Repository bytes are data, never authority.

No parser searches prose for a verdict, tool, session or success marker.
Unknown fields and duplicate JSON members are errors, including inside claims.
"""
from dataclasses import asdict
from datetime import datetime
import json

from jsonschema import Draft202012Validator

from .canonical import canonical_json
from .contracts import require
from .models import ArtifactRef, Budget, Encoding, RetentionClass, WorkerRole
from .provider import InvocationRequest, ScopeView, ToolDescriptor


def object_schema(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)


STRING = {'type': 'string'}
RESULT_SCHEMA = object_schema(dict(
    version={'const': 1}, invocation_id=STRING,
    status={'enum': ['COMPLETED', 'FAILED', 'TIMED_OUT', 'CANCELLED', 'REFUSED']},
    termination_reason={'enum': ['COMPLETED', 'DEADLINE', 'BUDGET', 'POLICY_STOP', 'PROVIDER_ERROR', 'HUMAN_STOP', 'REFUSAL']},
    session=object_schema(dict(id=STRING, fresh={'type': 'boolean'}, continued_from={'type': ['string', 'null']})),
    output=STRING,
    review={'anyOf': [{'type': 'null'}, object_schema(dict(review_spec_id=STRING,
        verdict={'enum': ['PASS', 'PASS_WITH_FINDINGS', 'FAIL', 'INCONCLUSIVE', 'ABSTAIN']}))]},
    claims={'type': 'array', 'items': object_schema(dict(subject=STRING, assertion=STRING,
        confidence={'type': 'number', 'minimum': 0, 'maximum': 1}))},
    proposed_mutations={'type': 'array', 'items': object_schema(dict(
        op={'enum': ['CREATE', 'MODIFY', 'DELETE', 'RENAME', 'CHMOD']}, path=STRING,
        content={'type': ['string', 'null']}, rename_to={'type': ['string', 'null']},
        before_digest={'type': ['string', 'null']}, mode={'type': ['integer', 'null']}))},
    requested_validations={'type': 'array', 'items': object_schema(dict(
        validation_spec_id=STRING, criterion_refs={'type': 'array', 'items': STRING, 'uniqueItems': True}))},
    tool_calls={'type': 'array', 'items': object_schema(dict(
        call_id=STRING, tool_id=STRING, arguments={'type': 'object'}))},
))
RESULT_VALIDATOR = Draft202012Validator(RESULT_SCHEMA)


def strict_json(data):
    def pairs(entries):
        result = {}
        for key, value in entries:
            require(key not in result, 'duplicate JSON member')  # guard:gr07_json_duplicate
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('nonfinite JSON number')  # guard:gr07_json_finite
    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def result_document(data, invocation_id):
    document = strict_json(data)
    require(not list(RESULT_VALIDATOR.iter_errors(document)), 'invalid result envelope')  # guard:gr07_envelope_schema
    require(document['invocation_id'] == invocation_id, 'result invocation mismatch')  # guard:gr07_envelope_identity
    reasons = {'COMPLETED': {'COMPLETED'}, 'FAILED': {'PROVIDER_ERROR', 'POLICY_STOP', 'BUDGET'},
               'TIMED_OUT': {'DEADLINE'}, 'CANCELLED': {'HUMAN_STOP', 'POLICY_STOP', 'BUDGET'}, 'REFUSED': {'REFUSAL'}}
    require(document['termination_reason'] in reasons[document['status']], 'inconsistent result status/reason')  # guard:gr07_envelope_reason
    return document


def artifact(document):
    values = dict(document)
    values['encoding'] = Encoding(values.get('encoding', 'IDENTITY'))
    values['retention_class'] = RetentionClass(values.get('retention_class', 'STANDARD'))
    return ArtifactRef(**values)


def request_bytes(request):
    values = asdict(request)
    values['deadline_at'] = request.deadline_at.isoformat()
    values['granted_capabilities'] = sorted(request.granted_capabilities)
    return canonical_json(values)


def request_from_bytes(data):
    values = strict_json(data)
    values['worker_role'] = WorkerRole(values['worker_role'])
    values['prompt_bundle_ref'] = artifact(values['prompt_bundle_ref'])
    scope = values['scope_view']
    values['scope_view'] = ScopeView(**dict(scope, file_index_ref=artifact(scope['file_index_ref']),
        include=tuple(scope['include']), exclude=tuple(scope['exclude'])))
    values['context_refs'] = tuple(artifact(a) for a in values['context_refs'])
    values['tool_surface'] = tuple(ToolDescriptor(**dict(t, input_schema_ref=artifact(t['input_schema_ref']),
        output_schema_ref=artifact(t['output_schema_ref']))) for t in values['tool_surface'])
    values['granted_capabilities'] = frozenset(values['granted_capabilities'])
    values['deadline_at'] = datetime.fromisoformat(values['deadline_at'])
    values['budget'] = Budget(**values['budget'])
    return InvocationRequest(**values)
