"""Workflow CRUD API routes with full node/edge management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
import uuid

from app.core.database import get_db
from app.models.models import Workflow, WorkflowNode, WorkflowEdge, Agent
from app.schemas.schemas import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    WorkflowNodeCreate, WorkflowNodeUpdate, WorkflowNodeResponse,
    WorkflowEdgeCreate, WorkflowEdgeResponse,
)

router = APIRouter()


# ─── Workflow CRUD ────────────────────────────────────────────────────

@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(agent_id: str = None, db: AsyncSession = Depends(get_db)):
    query = select(Workflow).options(
        selectinload(Workflow.nodes),
        selectinload(Workflow.edges),
    )
    if agent_id:
        query = query.where(Workflow.agent_id == agent_id)
    query = query.order_by(Workflow.updated_at.desc())
    result = await db.execute(query)
    return result.scalars().unique().all()


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.post("/", response_model=WorkflowResponse, status_code=201)
async def create_workflow(data: WorkflowCreate, db: AsyncSession = Depends(get_db)):
    # Verify agent exists
    agent_result = await db.execute(select(Agent).where(Agent.id == data.agent_id))
    if not agent_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    workflow = Workflow(
        agent_id=data.agent_id,
        name=data.name,
        description=data.description,
        variables=data.variables,
    )
    db.add(workflow)
    await db.flush()

    # Create nodes
    node_id_map = {}  # old_id -> new_id for edge remapping
    for node_data in data.nodes:
        old_id = node_data.id or str(uuid.uuid4())
        node = WorkflowNode(
            workflow_id=workflow.id,
            node_type=node_data.node_type,
            label=node_data.label,
            description=node_data.description,
            position_x=node_data.position_x,
            position_y=node_data.position_y,
            config=node_data.config,
        )
        db.add(node)
        await db.flush()
        node_id_map[old_id] = node.id

    # Create edges (remap node IDs)
    for edge_data in data.edges:
        source_id = node_id_map.get(edge_data.source_node_id, edge_data.source_node_id)
        target_id = node_id_map.get(edge_data.target_node_id, edge_data.target_node_id)
        edge = WorkflowEdge(
            workflow_id=workflow.id,
            source_node_id=source_id,
            target_node_id=target_id,
            label=edge_data.label,
            condition=edge_data.condition,
            edge_type=edge_data.edge_type,
            animated=edge_data.animated,
        )
        db.add(edge)

    await db.flush()

    # Reload with relationships
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow.id)
    )
    return result.scalar_one()


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: str, data: WorkflowUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    update_data = data.model_dump(exclude_unset=True, exclude={"nodes", "edges"})
    for field, value in update_data.items():
        setattr(workflow, field, value)

    # Full node/edge replacement if provided (for React Flow sync)
    if data.nodes is not None:
        # Delete old nodes and edges
        for edge in workflow.edges:
            await db.delete(edge)
        for node in workflow.nodes:
            await db.delete(node)
        await db.flush()

        # Create new nodes
        node_id_map = {}
        for node_data in data.nodes:
            old_id = node_data.id or str(uuid.uuid4())
            node = WorkflowNode(
                workflow_id=workflow.id,
                node_type=node_data.node_type,
                label=node_data.label,
                description=node_data.description,
                position_x=node_data.position_x,
                position_y=node_data.position_y,
                config=node_data.config,
            )
            db.add(node)
            await db.flush()
            node_id_map[old_id] = node.id

        if data.edges is not None:
            for edge_data in data.edges:
                source_id = node_id_map.get(edge_data.source_node_id, edge_data.source_node_id)
                target_id = node_id_map.get(edge_data.target_node_id, edge_data.target_node_id)
                edge = WorkflowEdge(
                    workflow_id=workflow.id,
                    source_node_id=source_id,
                    target_node_id=target_id,
                    label=edge_data.label,
                    condition=edge_data.condition,
                    edge_type=edge_data.edge_type,
                    animated=edge_data.animated,
                )
                db.add(edge)

    workflow.version += 1
    await db.flush()

    # Reload
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow.id)
    )
    return result.scalar_one()


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await db.delete(workflow)


@router.post("/{workflow_id}/activate", response_model=WorkflowResponse)
async def activate_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    """Set this workflow as the active workflow for its agent."""
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Deactivate other workflows for this agent
    other_workflows = await db.execute(
        select(Workflow).where(Workflow.agent_id == workflow.agent_id, Workflow.id != workflow_id)
    )
    for wf in other_workflows.scalars():
        wf.is_active = False

    workflow.is_active = True

    # Update agent's active workflow
    agent_result = await db.execute(select(Agent).where(Agent.id == workflow.agent_id))
    agent = agent_result.scalar_one()
    agent.active_workflow_id = workflow.id

    await db.flush()
    await db.refresh(workflow)
    return workflow


@router.post("/{workflow_id}/duplicate", response_model=WorkflowResponse)
async def duplicate_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    """Duplicate a workflow with all its nodes and edges."""
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    new_workflow = Workflow(
        agent_id=workflow.agent_id,
        name=f"{workflow.name} (Copy)",
        description=workflow.description,
        variables=workflow.variables,
        viewport=workflow.viewport,
    )
    db.add(new_workflow)
    await db.flush()

    node_id_map = {}
    for node in workflow.nodes:
        new_node = WorkflowNode(
            workflow_id=new_workflow.id,
            node_type=node.node_type,
            label=node.label,
            description=node.description,
            position_x=node.position_x,
            position_y=node.position_y,
            config=node.config,
        )
        db.add(new_node)
        await db.flush()
        node_id_map[node.id] = new_node.id

    for edge in workflow.edges:
        new_edge = WorkflowEdge(
            workflow_id=new_workflow.id,
            source_node_id=node_id_map.get(edge.source_node_id, edge.source_node_id),
            target_node_id=node_id_map.get(edge.target_node_id, edge.target_node_id),
            label=edge.label,
            condition=edge.condition,
            edge_type=edge.edge_type,
            animated=edge.animated,
        )
        db.add(new_edge)

    await db.flush()

    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == new_workflow.id)
    )
    return result.scalar_one()


# ─── Node CRUD ────────────────────────────────────────────────────────

@router.post("/{workflow_id}/nodes", response_model=WorkflowNodeResponse, status_code=201)
async def add_node(workflow_id: str, data: WorkflowNodeCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workflow not found")

    node = WorkflowNode(
        workflow_id=workflow_id,
        node_type=data.node_type,
        label=data.label,
        description=data.description,
        position_x=data.position_x,
        position_y=data.position_y,
        config=data.config,
    )
    db.add(node)
    await db.flush()
    await db.refresh(node)
    return node


@router.patch("/{workflow_id}/nodes/{node_id}", response_model=WorkflowNodeResponse)
async def update_node(
    workflow_id: str, node_id: str, data: WorkflowNodeUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkflowNode).where(
            WorkflowNode.id == node_id, WorkflowNode.workflow_id == workflow_id
        )
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(node, field, value)

    await db.flush()
    await db.refresh(node)
    return node


@router.delete("/{workflow_id}/nodes/{node_id}", status_code=204)
async def delete_node(workflow_id: str, node_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkflowNode).where(
            WorkflowNode.id == node_id, WorkflowNode.workflow_id == workflow_id
        )
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Also delete connected edges
    edges = await db.execute(
        select(WorkflowEdge).where(
            (WorkflowEdge.source_node_id == node_id) | (WorkflowEdge.target_node_id == node_id)
        )
    )
    for edge in edges.scalars():
        await db.delete(edge)

    await db.delete(node)


# ─── Edge CRUD ────────────────────────────────────────────────────────

@router.post("/{workflow_id}/edges", response_model=WorkflowEdgeResponse, status_code=201)
async def add_edge(workflow_id: str, data: WorkflowEdgeCreate, db: AsyncSession = Depends(get_db)):
    edge = WorkflowEdge(
        workflow_id=workflow_id,
        source_node_id=data.source_node_id,
        target_node_id=data.target_node_id,
        label=data.label,
        condition=data.condition,
        edge_type=data.edge_type,
        animated=data.animated,
    )
    db.add(edge)
    await db.flush()
    await db.refresh(edge)
    return edge


@router.delete("/{workflow_id}/edges/{edge_id}", status_code=204)
async def delete_edge(workflow_id: str, edge_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkflowEdge).where(
            WorkflowEdge.id == edge_id, WorkflowEdge.workflow_id == workflow_id
        )
    )
    edge = result.scalar_one_or_none()
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    await db.delete(edge)


# ─── Workflow Templates ───────────────────────────────────────────────

@router.get("/templates/list")
async def list_templates():
    """Return pre-built workflow templates."""
    return [
        {
            "id": "company_recognition",
            "name": "Şirket Tanıma",
            "description": "Firma sahibiyle konuşarak şirketi tanıyan akış",
            "category": "onboarding",
            "nodes": [
                {"node_type": "start", "label": "Başla", "position_x": 400, "position_y": 50,
                 "config": {}},
                {"node_type": "ai_prompt", "label": "Karşılama", "position_x": 400, "position_y": 150,
                 "config": {"prompt": "Merhaba! Ben şirketinizi tanımak için buradayım. Öncelikle isminizi öğrenebilir miyim?", "save_response_to": "owner_name"}},
                {"node_type": "question", "label": "Şirket Adı", "position_x": 400, "position_y": 270,
                 "config": {"question_text": "Şirketinizin adı nedir?", "save_to_variable": "company_name", "expected_type": "text"}},
                {"node_type": "question", "label": "Ülke/Şehir", "position_x": 400, "position_y": 390,
                 "config": {"question_text": "Hangi ülke ve şehirde faaliyet gösteriyorsunuz?", "save_to_variable": "location", "expected_type": "text"}},
                {"node_type": "question", "label": "Sektör", "position_x": 400, "position_y": 510,
                 "config": {"question_text": "Hangi sektörde faaliyet gösteriyorsunuz?", "save_to_variable": "sector", "expected_type": "choice",
                            "choices": ["Teknoloji", "Sağlık", "Eğitim", "Finans", "Perakende", "Üretim", "Hizmet", "Diğer"]}},
                {"node_type": "question", "label": "Hizmetler", "position_x": 400, "position_y": 630,
                 "config": {"question_text": "Şirketiniz hangi hizmetleri veya ürünleri sunuyor?", "save_to_variable": "services", "expected_type": "text"}},
                {"node_type": "question", "label": "Çalışan Sayısı", "position_x": 400, "position_y": 750,
                 "config": {"question_text": "Yaklaşık kaç çalışanınız var?", "save_to_variable": "employee_count", "expected_type": "choice",
                            "choices": ["1-5", "5-10", "10-50", "50-200", "200+"]}},
                {"node_type": "question", "label": "Hedef Müşteri", "position_x": 400, "position_y": 870,
                 "config": {"question_text": "Hedef müşteri kitleniz kimler?", "save_to_variable": "target_customers", "expected_type": "text"}},
                {"node_type": "question", "label": "Sorunlar", "position_x": 400, "position_y": 990,
                 "config": {"question_text": "Şu anda en büyük iş zorluklarınız neler?", "save_to_variable": "pain_points", "expected_type": "text"}},
                {"node_type": "ai_prompt", "label": "Özet & Onay", "position_x": 400, "position_y": 1110,
                 "config": {"prompt": "Aldığım bilgileri özetleyeceğim. {{company_name}} şirketi, {{location}} merkezli, {{sector}} sektöründe faaliyet gösteren bir firma. {{services}} hizmetlerini sunuyorsunuz. Bu bilgiler doğru mu?", "save_response_to": "confirmation"}},
                {"node_type": "end", "label": "Bitir", "position_x": 400, "position_y": 1230,
                 "config": {}},
            ],
            "edges": "sequential",
        },
        {
            "id": "customer_support",
            "name": "Müşteri Destek",
            "description": "Müşteri sorunlarını çözen destek akışı",
            "category": "support",
            "nodes": [
                {"node_type": "start", "label": "Başla", "position_x": 400, "position_y": 50},
                {"node_type": "ai_prompt", "label": "Karşılama", "position_x": 400, "position_y": 150,
                 "config": {"prompt": "Hoş geldiniz! Size nasıl yardımcı olabilirim?", "save_response_to": "initial_request"}},
                {"node_type": "condition", "label": "Sorun Tipi", "position_x": 400, "position_y": 300,
                 "config": {"conditions": [
                     {"variable": "issue_type", "operator": "equals", "value": "technical"},
                     {"variable": "issue_type", "operator": "equals", "value": "billing"},
                     {"variable": "issue_type", "operator": "equals", "value": "general"},
                 ]}},
                {"node_type": "ai_prompt", "label": "Teknik Destek", "position_x": 150, "position_y": 450,
                 "config": {"prompt": "Teknik sorununuzu anlamamız için biraz daha detay verebilir misiniz?"}},
                {"node_type": "ai_prompt", "label": "Fatura/Ödeme", "position_x": 400, "position_y": 450,
                 "config": {"prompt": "Fatura veya ödeme konusunda size yardımcı olayım."}},
                {"node_type": "ai_prompt", "label": "Genel Bilgi", "position_x": 650, "position_y": 450,
                 "config": {"prompt": "Genel bilgi talebinizi dinliyorum."}},
                {"node_type": "knowledge_lookup", "label": "Bilgi Ara", "position_x": 400, "position_y": 600,
                 "config": {"query_variable": "caller_question", "max_results": 3}},
                {"node_type": "ai_prompt", "label": "Çözüm Sun", "position_x": 400, "position_y": 750,
                 "config": {"prompt": "Bulduğum bilgilere göre çözüm önerim: {{answer}}. Bu yardımcı oldu mu?"}},
                {"node_type": "condition", "label": "Çözüldü mü?", "position_x": 400, "position_y": 900,
                 "config": {"conditions": [
                     {"variable": "resolved", "operator": "equals", "value": "yes"},
                     {"variable": "resolved", "operator": "equals", "value": "no"},
                 ]}},
                {"node_type": "transfer", "label": "Uzman Yönlendir", "position_x": 200, "position_y": 1050,
                 "config": {"transfer_to": "human_agent", "transfer_message": "Sizi bir uzmanımıza bağlıyorum"}},
                {"node_type": "end", "label": "Bitir", "position_x": 500, "position_y": 1050},
            ],
            "edges": "custom",
        },
        {
            "id": "outbound_sales",
            "name": "Satış Araması",
            "description": "Outbound satış araması akışı",
            "category": "sales",
        },
        {
            "id": "appointment_booking",
            "name": "Randevu Alma",
            "description": "Müşteriden randevu alan akış",
            "category": "booking",
        },
        {
            "id": "survey",
            "name": "Anket / Geri Bildirim",
            "description": "Müşteri memnuniyet anketi akışı",
            "category": "feedback",
        },
    ]
