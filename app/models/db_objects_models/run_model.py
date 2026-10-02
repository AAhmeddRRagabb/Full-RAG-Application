from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from models.db_schemas import Run, RunStep

from .base_obj_model import BaseObjModel


class RunModel(BaseObjModel):
    def __init__(self, db_client):
        super().__init__(db_client = db_client)


    async def insert_run(self, run: Run) -> bool:
        session: AsyncSession

        try:
            async with self.db_client() as session:
                session.add(run)
                await session.commit()
                await session.refresh(run)

        except Exception as e:
            self.logger.error(f"Error Inserting Run: {e}")
            return False

        return True


    async def finish_run(
        self,
        run_id    : int,
        status    : str,
        response  : str | None = None,
        error     : str | None = None,
        duration_s: float | None = None,
    ) -> bool:
        session: AsyncSession

        try:
            async with self.db_client() as session:
                run = await session.get(Run, run_id)
                if run is None:
                    return False

                run.status = status
                run.response = response
                run.error = error
                run.duration_s = duration_s
                run.completed_at = datetime.now(timezone.utc)

                await session.commit()

        except Exception as e:
            self.logger.error(f"Error Finishing Run: {e}")
            return False

        return True


    async def insert_steps(self, steps: list[RunStep]) -> bool:
        if not steps:
            return True

        session: AsyncSession

        try:
            async with self.db_client() as session:
                session.add_all(steps)
                await session.commit()

        except Exception as e:
            self.logger.error(f"Error Inserting Run Steps: {e}")
            return False

        return True



    async def fail_run(self, run_id: int, error: str, time_taken: float, response: str | None = None) -> bool:
        try:
            await self.finish_run(
                run_id = run_id,
                status = "failed",
                response = response,
                error = error,
                # duration_s = round((time.perf_counter() - started_at) * 1000, 2),
                duration_s = time_taken,
            )
        except Exception:
            self.logger("Error Failing Run")
            return False

        return True
