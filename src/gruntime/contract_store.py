"""Contract persistence. Content, run bindings and grant provenance are pinned.

Activation and its audit event, nonce claims, run binding and status are written
in the controller's single SQLite transaction. Status never changes the hash.
"""
import json

from .authority import ContractActivationRecord
from .canonical import canonical_json
from .contracts import StageContract, require

CONTRACT_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS contracts (contract_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id), stage_id TEXT NOT NULL, status TEXT NOT NULL, document TEXT NOT NULL) STRICT",
    "CREATE TABLE IF NOT EXISTS activations (activation_id TEXT PRIMARY KEY, contract_id TEXT NOT NULL REFERENCES contracts(contract_id), run_id TEXT NOT NULL UNIQUE REFERENCES runs(run_id), document TEXT NOT NULL) STRICT",
    "CREATE TABLE IF NOT EXISTS grant_nonces (nonce TEXT PRIMARY KEY, decision_id TEXT NOT NULL UNIQUE REFERENCES decisions(decision_id), activation_id TEXT NOT NULL REFERENCES activations(activation_id)) STRICT",
    "CREATE TABLE IF NOT EXISTS policy_evaluations (evaluation_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id), document TEXT NOT NULL) STRICT",
)


class ContractStore:
    def put_contract(self, contract):
        contract = StageContract(contract.document())
        row = self.connection.execute("SELECT document FROM contracts WHERE contract_id=?", (contract.contract_id,)).fetchone()
        if row:
            before = StageContract(json.loads(row[0]))
            require({k: v for k, v in before.document().items() if k != "status"} == {k: v for k, v in contract.document().items() if k != "status"}, "XC-13/INV-07: frozen contract content is immutable")  # guard:gr06_contract_immutable
            legal = {"DRAFT": {"ACTIVE", "REVOKED"}, "ACTIVE": {"FULFILLED", "REVOKED", "EXPIRED", "SUPERSEDED"}}
            require(contract.status == before.status or contract.status in legal.get(before.status, set()), "illegal contract lifecycle transition")  # guard:gr06_contract_lifecycle
        else:
            require(contract.status == "DRAFT", "new persisted contract must be DRAFT")  # guard:gr06_persist_draft
        if contract.status == "ACTIVE":
            binding = self.connection.execute("SELECT 1 FROM activations WHERE contract_id=?", (contract.contract_id,)).fetchone()
            require(binding is not None, "ACTIVE requires an activation record")  # guard:gr06_active_record
            other = self.connection.execute("SELECT 1 FROM contracts WHERE stage_id=? AND status='ACTIVE' AND contract_id<>?", (contract.stage_id, contract.contract_id)).fetchone()
            require(other is None, "another contract is ACTIVE for this stage")  # guard:gr06_single_active
        self.connection.execute("INSERT INTO contracts VALUES (?,?,?,?,?) ON CONFLICT(contract_id) DO UPDATE SET status=excluded.status, document=excluded.document",
            (contract.contract_id, contract.project_id, contract.stage_id, contract.status, contract._encoded.decode()))

    def get_contract(self, contract_id):
        row = self.connection.execute("SELECT * FROM contracts WHERE contract_id=?", (contract_id,)).fetchone()
        if row is None:
            raise KeyError(contract_id)
        contract = StageContract(json.loads(row["document"]))
        require((contract.contract_id, contract.project_id, contract.stage_id, contract.status) == (row["contract_id"], row["project_id"], row["stage_id"], row["status"]), "contract persistence binding mismatch")  # guard:gr06_contract_storage_binding
        return contract

    def put_activation(self, activation):
        activation.verify()
        contract = self.get_contract(activation.contract_id)
        run = self.get_run(activation.run_id)
        require(activation.contract_hash == contract.contract_hash and activation.project_id == contract.project_id == run.project_id and contract.stage_id == run.stage_id, "activation persistence binding mismatch")  # guard:gr06_persist_activation_binding
        row = self.connection.execute("SELECT document FROM activations WHERE activation_id=? OR run_id=?", (activation.activation_id, activation.run_id)).fetchone()
        require(row is None or row[0] == activation._encoded.decode(), "activation and effective capabilities are immutable")  # guard:gr06_activation_immutable
        self.connection.execute("INSERT OR IGNORE INTO activations VALUES (?,?,?,?)", (activation.activation_id, activation.contract_id, activation.run_id, activation._encoded.decode()))

    def get_activation(self, activation_id):
        row = self.connection.execute("SELECT * FROM activations WHERE activation_id=?", (activation_id,)).fetchone()
        if row is None:
            raise KeyError(activation_id)
        activation = ContractActivationRecord(json.loads(row["document"]))
        require((activation.activation_id, activation.contract_id, activation.run_id) == (row["activation_id"], row["contract_id"], row["run_id"]), "activation storage binding mismatch")  # guard:gr06_activation_storage_binding
        return activation

    def activation_for_run(self, run_id):
        row = self.connection.execute("SELECT activation_id FROM activations WHERE run_id=?", (run_id,)).fetchone()
        return None if row is None else self.get_activation(row[0])

    def put_policy_evaluation(self, evaluation):
        document = canonical_json(evaluation).decode()
        row = self.connection.execute("SELECT document FROM policy_evaluations WHERE evaluation_id=?", (evaluation["evaluation_id"],)).fetchone()
        require(row is None or row[0] == document, "policy evaluations are immutable")  # guard:gr06_policy_immutable
        self.connection.execute("INSERT OR IGNORE INTO policy_evaluations VALUES (?,?,?)", (evaluation["evaluation_id"], evaluation["project_id"], document))

    def get_policy_evaluation(self, evaluation_id):
        row = self.connection.execute("SELECT document FROM policy_evaluations WHERE evaluation_id=?", (evaluation_id,)).fetchone()
        if row is None:
            raise KeyError(evaluation_id)
        return json.loads(row[0])
