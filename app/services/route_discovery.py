# app/services/route_discovery.py
from sqlalchemy import select
from app.models.route import Route


async def get_or_create_route(session, origin: str, destination: str) -> Route:
    origin_n, dest_n = origin.strip().title(), destination.strip().title()

    result = await session.execute(
        select(Route).where(
            Route.origin_city == origin_n,
            Route.destination_city == dest_n,
        )
    )
    route = result.scalar_one_or_none()
    if route:
        return route

    # New route — register it, scheduled job will pick it up next run
    route = Route(
        origin_city=origin_n,
        destination_city=dest_n,
        is_active=True,
    )
    session.add(route)
    await session.commit()
    await session.refresh(route)
    return route