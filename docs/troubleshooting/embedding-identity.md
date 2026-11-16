# Embedding model identity in management

New knowledge bases resolve their embedding model within the selected tenant and
store the complete registered name plus provider (for example,
`bge-m3___VLLM@VLLM`). Management model options now preserve that identity.
The provider suffix is an identity, not the model name sent to the embedding HTTP
endpoint. Management parsing strips the internal `___` suffix only after selecting
the tenant's exact configuration.

Legacy short names remain accepted by management parsing only when the match is
unique. Ambiguous names fail instead of selecting the newest credentials. This
compatibility does not repair old identifiers in the core retrieval API. Existing
knowledge bases and vectors are not migrated. Do not directly rename a populated
knowledge base's model or tenant records: verify the exact original model,
provider, tenant and index before choosing a migration or rebuilding a new KB.

The legacy management-only `Custom` provider is preserved, not reassigned to a
provider with a different protocol. Core retrieval support for `Custom` is not
added here. Model identity consistency also does not imply support for every
provider's HTTP API in the management parser.

These changes address a reproduced identifier mismatch related to reports #227
and #229; the original installations were not reproduced. Tests use synthetic
records and substituted database/model boundaries, not live model endpoints.
Deploy the management server and web changes together.
