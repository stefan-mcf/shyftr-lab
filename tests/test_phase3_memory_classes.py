from __future__ import annotations

from pathlib import Path

from shyftr.continuity import ContinuityPackRequest, assemble_continuity_pack
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl, read_jsonl
from shyftr.live_context import LiveContextCaptureRequest, SessionHarvestRequest, capture_live_context, harvest_session
from shyftr.memory_classes import class_spec, infer_memory_type, resolve_memory_type, validate_resource_memory
from shyftr.provider.memory import remember, search
from shyftr.store.sqlite import open_sqlite, rebuild_from_cell


def test_memory_class_defaults_and_legacy_compatibility_helpers():
    spec = class_spec(None, kind='workflow', trust_tier='trace')
    assert spec is not None
    assert spec.memory_type == 'procedural'
    assert spec.authority == 'review_gated'
    assert resolve_memory_type(None, kind='preference') == 'semantic'
    assert infer_memory_type(entry_kind='artifact_ref') == 'resource'


def test_remember_and_search_round_trip_memory_type(tmp_path: Path):
    cell = init_cell(tmp_path, 'memory-cell', cell_type='memory')
    resource = remember(
        cell,
        'file:/tmp/report.md is the canonical handoff artifact',
        'tool_quirk',
        metadata={'resource_ref': 'file:/tmp/report.md'},
        memory_type='resource',
    )
    semantic = remember(cell, 'User prefers compact handoff packets.', 'preference')

    resource_results = search(cell, 'report artifact', memory_types=['resource'])
    semantic_results = search(cell, 'compact closeout', memory_types=['semantic'])

    assert [row.memory_id for row in resource_results] == [resource.memory_id]
    assert resource_results[0].memory_type == 'resource'
    assert [row.memory_id for row in semantic_results] == [semantic.memory_id]
    assert semantic_results[0].memory_type == 'semantic'


def test_resource_memory_requires_reference_handle():
    try:
        validate_resource_memory('This is just blob content with no handle.', {})
    except ValueError as exc:
        assert 'reference/handle' in str(exc)
    else:
        raise AssertionError('resource validation should fail without a reference')


def test_continuity_pack_labels_memory_type(tmp_path: Path):
    memory_cell = init_cell(tmp_path, 'memory-cell', cell_type='memory')
    continuity_cell = init_cell(tmp_path, 'continuity-cell', cell_type='continuity')
    remember(memory_cell, 'Use deterministic verification recipes before release.', 'verification_heuristic')
    pack = assemble_continuity_pack(
        ContinuityPackRequest(
            memory_cell_path=str(memory_cell),
            continuity_cell_path=str(continuity_cell),
            runtime_id='runtime',
            session_id='session',
            compaction_id='cmp',
            query='verification recipes release',
            mode='advisory',
            write=False,
        )
    )
    assert pack.items
    assert pack.items[0].memory_type == 'procedural'


def test_harvest_proposals_include_memory_type_boundaries(tmp_path: Path):
    live_cell = init_cell(tmp_path, 'live-cell', cell_type='live_context')
    continuity_cell = init_cell(tmp_path, 'continuity-cell', cell_type='continuity')
    memory_cell = init_cell(tmp_path, 'memory-cell', cell_type='memory')

    capture_live_context(LiveContextCaptureRequest(
        cell_path=str(live_cell), runtime_id='runtime', session_id='session', task_id='task',
        entry_kind='artifact_ref', content='file:/tmp/evidence.png', source_ref='synthetic:test',
        retention_hint='durable', sensitivity_hint='public', write=True,
    ))
    capture_live_context(LiveContextCaptureRequest(
        cell_path=str(live_cell), runtime_id='runtime', session_id='session', task_id='task',
        entry_kind='goal', content='Continue the unresolved debug pass.', source_ref='synthetic:test',
        retention_hint='session', sensitivity_hint='internal', write=True,
    ))

    report = harvest_session(SessionHarvestRequest(
        live_cell_path=str(live_cell), continuity_cell_path=str(continuity_cell), memory_cell_path=str(memory_cell),
        runtime_id='runtime', session_id='session', write=True,
    ))
    proposals = [record for _, record in read_jsonl(live_cell / 'ledger' / 'session_harvest_proposals.jsonl')]
    memory_types = {proposal['memory_type'] for proposal in proposals}
    assert 'resource' in memory_types
    assert 'continuity' in memory_types
    assert report.bucket_counts['memory_candidate'] >= 1
    assert report.bucket_counts['continuity_feedback'] >= 1


def test_sqlite_rebuild_preserves_memory_type_for_mixed_rows(tmp_path: Path):
    cell = init_cell(tmp_path, 'memory-cell', cell_type='memory')
    remember(cell, 'User prefers terminal-first summaries.', 'preference')
    append_jsonl(
        cell / 'traces' / 'approved.jsonl',
        {
            'trace_id': 'trace-legacy',
            'cell_id': 'memory-cell',
            'statement': 'Legacy workflow memory without explicit memory_type.',
            'source_fragment_ids': ['frag-legacy'],
            'kind': 'workflow',
            'status': 'approved',
            'confidence': 0.7,
            'tags': ['legacy'],
            'use_count': 0,
            'success_count': 0,
            'failure_count': 0,
        },
    )

    db = tmp_path / 'store.db'
    conn = open_sqlite(db)
    try:
        rebuild_from_cell(conn, cell)
        rows = conn.execute('SELECT trace_id, memory_type FROM traces ORDER BY trace_id').fetchall()
    finally:
        conn.close()

    row_map = {trace_id: memory_type for trace_id, memory_type in rows}
    assert row_map['trace-legacy'] == 'procedural'
    assert 'semantic' in set(value for value in row_map.values() if value)
