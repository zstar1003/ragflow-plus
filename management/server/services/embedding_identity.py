"""Tenant-local embedding identities; never choose credentials by list order."""


def model_identity(row):
    name = row.get('llm_name')
    if not isinstance(name, str) or not name:
        raise ValueError('嵌入模型名称为空')
    factory = row.get('llm_factory')
    # Custom is a legacy management-only provider, not in the core registry.
    # Preserve its existing identifier; this patch does not add core support.
    return f'{name}@{factory}' if factory and factory != 'Custom' else name


def select_embedding(rows, requested=None):
    rows = [r for r in rows if isinstance(r.get('llm_name'), str) and r['llm_name']]
    if requested is None:
        if not rows:
            raise ValueError('租户未配置嵌入模型')
        return rows[0]
    # Qualified and stored names win over historical stripped aliases. All
    # ambiguous matches fail closed, including duplicate names across providers.
    for match in (
        lambda r: model_identity(r) == requested,
        lambda r: r['llm_name'] == requested,
        lambda r: r['llm_name'].split('___')[0] == requested,
    ):
        matches = [r for r in rows if match(r)]
        if matches:
            if len(matches) != 1:
                raise ValueError('嵌入模型名称有歧义，请选择包含提供商的完整模型标识')
            return matches[0]
    raise ValueError('知识库所属租户未配置匹配的嵌入模型')
