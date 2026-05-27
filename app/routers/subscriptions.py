import json

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.database import get_session_factory
from app.models.subscription import Subscription
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
)

router = APIRouter()


def _to_response(sub: Subscription) -> SubscriptionResponse:
    extra = []
    if sub.extra_sources:
        try:
            extra = json.loads(sub.extra_sources)
        except (json.JSONDecodeError, TypeError):
            extra = []
    return SubscriptionResponse(
        id=sub.id,
        repo_owner=sub.repo_owner,
        repo_name=sub.repo_name,
        extra_sources=extra,
        active=sub.active,
        created_at=sub.created_at,
        updated_at=sub.updated_at,
    )


@router.get("", response_model=SubscriptionListResponse)
async def list_subscriptions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> SubscriptionListResponse:
    factory = get_session_factory()
    async with factory() as session:
        total_r = await session.execute(select(func.count(Subscription.id)))
        total = total_r.scalar_one()

        result = await session.execute(
            select(Subscription)
            .order_by(Subscription.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        subs = result.scalars().all()

    items = [_to_response(s) for s in subs]
    return SubscriptionListResponse(total=total, items=items)


@router.post("", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(body: SubscriptionCreate) -> SubscriptionResponse:
    factory = get_session_factory()
    async with factory() as session:
        # 检查是否已订阅同一仓库
        existing = await session.execute(
            select(Subscription).where(
                Subscription.repo_owner == body.repo_owner,
                Subscription.repo_name == body.repo_name,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409,
                detail=f"已订阅 {body.repo_owner}/{body.repo_name}，请勿重复添加",
            )

        sub = Subscription(
            repo_owner=body.repo_owner,
            repo_name=body.repo_name,
            extra_sources=json.dumps(body.extra_sources, ensure_ascii=False) if body.extra_sources else None,
            active=True,
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return _to_response(sub)


@router.get("/{sub_id}", response_model=SubscriptionResponse)
async def get_subscription(sub_id: int) -> SubscriptionResponse:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(Subscription).where(Subscription.id == sub_id))
        sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail=f"订阅 {sub_id} 不存在")
    return _to_response(sub)


@router.put("/{sub_id}", response_model=SubscriptionResponse)
async def update_subscription(sub_id: int, body: SubscriptionUpdate) -> SubscriptionResponse:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(Subscription).where(Subscription.id == sub_id))
        sub = result.scalar_one_or_none()
        if sub is None:
            raise HTTPException(status_code=404, detail=f"订阅 {sub_id} 不存在")

        if body.repo_owner is not None:
            sub.repo_owner = body.repo_owner
        if body.repo_name is not None:
            sub.repo_name = body.repo_name
        if body.extra_sources is not None:
            sub.extra_sources = json.dumps(body.extra_sources, ensure_ascii=False)
        if body.active is not None:
            sub.active = body.active

        await session.commit()
        await session.refresh(sub)
        return _to_response(sub)


@router.delete("/{sub_id}", status_code=204)
async def delete_subscription(sub_id: int) -> None:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(Subscription).where(Subscription.id == sub_id))
        sub = result.scalar_one_or_none()
        if sub is None:
            raise HTTPException(status_code=404, detail=f"订阅 {sub_id} 不存在")
        await session.delete(sub)
        await session.commit()
