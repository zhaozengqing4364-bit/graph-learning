"""Article workspace API tests."""

import pytest


@pytest.mark.asyncio
async def test_article_crud_and_workspace_bundle(app_client, db_conn):
    topic_id = "tp_articles"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status, source_type, source_content) VALUES (?, ?, 'active', 'article', ?)",
        (topic_id, "Article Topic", "seed source"),
    )
    await db_conn.commit()

    create_response = await app_client.post(
        f"/api/v1/topics/{topic_id}/articles",
        json={"title": "第一篇源文章", "body": "这是一篇源文章。"},
    )
    assert create_response.status_code == 200
    create_data = create_response.json()["data"]
    assert create_data["article"]["article_id"].startswith("source:")
    assert create_data["article"]["title"] == "第一篇源文章"

    article_id = create_data["article"]["article_id"]

    list_response = await app_client.get(f"/api/v1/topics/{topic_id}/articles")
    assert list_response.status_code == 200
    list_data = list_response.json()["data"]
    assert len(list_data) == 1
    assert list_data[0]["article_id"] == article_id

    detail_response = await app_client.get(f"/api/v1/topics/{topic_id}/articles/{article_id}")
    assert detail_response.status_code == 200
    detail_data = detail_response.json()["data"]
    assert detail_data["article_id"] == article_id
    assert detail_data["body"] == "这是一篇源文章。"

    bundle_response = await app_client.get(f"/api/v1/topics/{topic_id}/workspace")
    assert bundle_response.status_code == 200
    bundle = bundle_response.json()["data"]
    assert len(bundle["source_articles"]) == 1
    assert bundle["concept_notes"] == []
    assert bundle["reading_state"] is None


@pytest.mark.asyncio
async def test_article_analysis_candidates_backlinks_and_removal(app_client, db_conn):
    topic_id = "tp_article_analysis"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Analysis Topic"),
    )
    await db_conn.commit()

    create_response = await app_client.post(
        f"/api/v1/topics/{topic_id}/articles",
        json={
            "title": "GNN 笔记",
            "body": "第一段。\n\n第二段提到 [[消息传递]] 如何聚合邻居。\n\n第三段。",
        },
    )
    assert create_response.status_code == 200
    create_data = create_response.json()["data"]
    article_id = create_data["article"]["article_id"]
    assert create_data["analysis"]["candidate_count"] == 1

    candidates_response = await app_client.get(f"/api/v1/topics/{topic_id}/concept-candidates")
    assert candidates_response.status_code == 200
    candidates = candidates_response.json()["data"]
    assert len(candidates) == 1
    assert candidates[0]["concept_text"] == "消息传递"
    candidate_id = candidates[0]["candidate_id"]

    confirm_response = await app_client.post(
        f"/api/v1/topics/{topic_id}/concept-candidates/{candidate_id}/confirm",
        json={},
    )
    assert confirm_response.status_code == 200
    confirmed = confirm_response.json()["data"]
    assert confirmed["status"] == "confirmed"
    assert confirmed["matched_node_id"].startswith("nd_")
    node_id = confirmed["matched_node_id"]

    backlinks_response = await app_client.get(f"/api/v1/topics/{topic_id}/nodes/{node_id}/backlinks")
    assert backlinks_response.status_code == 200
    backlinks = backlinks_response.json()["data"]
    assert len(backlinks) == 1
    assert backlinks[0]["article_id"] == article_id
    assert backlinks[0]["anchor_id"] == f"{article_id}:paragraph:1"

    update_response = await app_client.patch(
        f"/api/v1/topics/{topic_id}/articles/{article_id}",
        json={"body": "文章已改写，不再提及原来的概念。"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["analysis"]["removed_mentions"] == 1

    backlinks_after_removal = await app_client.get(f"/api/v1/topics/{topic_id}/nodes/{node_id}/backlinks")
    assert backlinks_after_removal.status_code == 200
    assert backlinks_after_removal.json()["data"] == []

    candidates_after_removal = await app_client.get(f"/api/v1/topics/{topic_id}/concept-candidates")
    assert candidates_after_removal.status_code == 200
    assert candidates_after_removal.json()["data"][0]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_concept_notes_and_reading_state(app_client, db_conn):
    topic_id = "tp_workspace_state"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Workspace Topic"),
    )
    await db_conn.commit()

    note_response = await app_client.put(
        f"/api/v1/topics/{topic_id}/concept-notes/nd_message",
        json={"title": "消息传递", "body": "聚合和更新要分开理解。"},
    )
    assert note_response.status_code == 200
    note = note_response.json()["data"]
    assert note["concept_key"] == "nd_message"
    assert note["body"] == "聚合和更新要分开理解。"

    note_detail = await app_client.get(f"/api/v1/topics/{topic_id}/concept-notes/nd_message")
    assert note_detail.status_code == 200
    assert note_detail.json()["data"]["title"] == "消息传递"

    reading_response = await app_client.put(
        f"/api/v1/topics/{topic_id}/reading-state",
        json={
            "article_id": "concept:nd_message",
            "scroll_top": 320,
            "trail": [
                {"article_id": "guide:tp_workspace_state", "title": "Workspace Topic"},
                {"article_id": "concept:nd_message", "title": "消息传递"},
            ],
            "completed_article_ids": ["guide:tp_workspace_state"],
        },
    )
    assert reading_response.status_code == 200
    reading_data = reading_response.json()["data"]
    assert reading_data["article_id"] == "concept:nd_message"
    assert reading_data["completed_article_ids"] == ["guide:tp_workspace_state"]

    reading_detail = await app_client.get(f"/api/v1/topics/{topic_id}/reading-state")
    assert reading_detail.status_code == 200
    assert reading_detail.json()["data"]["scroll_top"] == 320


@pytest.mark.asyncio
async def test_manual_candidate_ignore_and_search(app_client, db_conn):
    topic_id = "tp_candidate_actions"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Candidate Topic"),
    )
    await db_conn.commit()

    article_response = await app_client.post(
        f"/api/v1/topics/{topic_id}/articles",
        json={"title": "候选文章", "body": "这里没有显式链接。"},
    )
    article_id = article_response.json()["data"]["article"]["article_id"]

    candidate_response = await app_client.post(
        f"/api/v1/topics/{topic_id}/concept-candidates",
        json={
            "concept_text": "图读出",
            "source_article_id": article_id,
            "origin": "manual",
        },
    )
    assert candidate_response.status_code == 200
    candidate = candidate_response.json()["data"]
    assert candidate["status"] == "candidate"

    ignore_response = await app_client.post(
        f"/api/v1/topics/{topic_id}/concept-candidates/{candidate['candidate_id']}/ignore",
        json={},
    )
    assert ignore_response.status_code == 200
    assert ignore_response.json()["data"]["status"] == "ignored"

    search_response = await app_client.get(
        f"/api/v1/topics/{topic_id}/workspace-search",
        params={"q": "候选"},
    )
    assert search_response.status_code == 200
    search_data = search_response.json()["data"]
    assert len(search_data["articles"]) == 1
    assert search_data["articles"][0]["title"] == "候选文章"
