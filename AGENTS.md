# Working on Prento

Read [DESIGN.md](DESIGN.md) first; [README.md](README.md) is the user entry point.

- Preserve the four combinations: push/credit × FIFO/priority. A fair comparison changes one variable at a time.
- No Homa transport dependency, production capacity claim, universal latency guarantee or exactly-once claim.
- `make test` verifies real TCP processes plus accounting and core invariants. `make sanitize` runs address/undefined sanitizers separately from release builds. Run new behavior tests before implementation.
- No silent drops: preserve one terminal outcome per generated logical ID. A missing ACK means delivery can be unknown. Never equate socket receipt with sink completion or durability.
- Native process RSS does not include all kernel socket memory. Synthetic queued payload bytes are logical sizes, not materialized allocations.
- Batches are non-preemptive. Priority classes are workload labels, not a production alert classifier.
- Raw benchmark runs, configuration and environment must accompany results. Never replace measurements with estimated improvements. Do not overwrite nonempty run directories.
- Before packaging claims, run the relevant Docker target and demo. Kubernetes manifests alone do not establish multi-node scalability.
- Record actual design changes, failed checks and verification in docs/AGENT_WORKFLOW.md. Do not invent agent failures or human review decisions.
- Do not publish, push, operate production switches or modify unrelated workspace projects without user authorization.
