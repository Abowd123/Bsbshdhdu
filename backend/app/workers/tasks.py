import asyncio
from datetime import datetime, timezone
from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.bot import Bot, BotStatus
from app.services.docker_engine import docker_engine
from app.services.monitoring_service import monitoring_service


async def _monitor_bots_health() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Bot).where(Bot.status == BotStatus.RUNNING, Bot.auto_restart == True))
        bots = result.scalars().all()
        for bot in bots:
            docker_status = await docker_engine.get_status(bot.container_name)
            if docker_status in ("exited", "not_found"):
                bot.status = BotStatus.CRASHED
                bot.restart_count += 1
                await db.commit()
                try:
                    container_id = await docker_engine.create_and_start(
                        container_name=bot.container_name,
                        host_bot_path=bot.storage_path,
                        entrypoint=bot.entrypoint,
                        env_vars=bot.env_vars or {},
                        cpu_limit=bot.cpu_limit,
                        ram_limit_mb=bot.ram_limit_mb,
                        disk_limit_mb=bot.disk_limit_mb,
                        process_limit=bot.process_limit,
                    )
                    bot.container_id = container_id
                    bot.status = BotStatus.RUNNING
                except Exception as exc:
                    bot.status = BotStatus.ERROR
                    bot.last_error = str(exc)
                await db.commit()


@celery_app.task(name="app.workers.tasks.monitor_bots_health")
def monitor_bots_health() -> None:
    asyncio.run(_monitor_bots_health())


async def _collect_running_bots_stats() -> None:
    """يمر على كل البوتات الشغّالة ويجمع قراءة موارد لكل واحدة ويخزّنها في Redis."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Bot).where(Bot.status == BotStatus.RUNNING))
        bots = result.scalars().all()
        for bot in bots:
            try:
                await monitoring_service.collect_and_store(str(bot.id), bot.container_name)
            except Exception:
                # لا نوقف بقية البوتات بسبب فشل قراءة واحدة
                continue


@celery_app.task(name="app.workers.tasks.collect_bots_stats")
def collect_bots_stats() -> None:
    asyncio.run(_collect_running_bots_stats())
