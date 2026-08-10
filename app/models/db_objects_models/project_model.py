# ----------------------------------------------------
# Building a database model for projects
# ----------------------------------------------------


from .base_obj_model import BaseObjModel, ObjectModelResult

from models.enums import ResponsesEnum
from models.db_schemas import Project

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

class ProjectModel(BaseObjModel):
    """
    Data model for the project table
    """
    def __init__(self, db_client):
        super().__init__(db_client)
        


    async def insert_project(self, project: Project) -> ObjectModelResult:
        """
        Returns:
            ObjectModelResult:
                if success -> content: the project
                if failure -> error & respone message
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    session.add(project)

                await session.commit()  
                await session.refresh(project)
        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.PROJECT_INNER_ERROR.value)

        return self._return_success(content = project)
    

    async def get_project_or_insert_it(self, project_name: str) -> ObjectModelResult:
        """
        Returns:
            ObjectModelResult:
                if success -> content: the project
                if failure -> error & respone message
        """
        session: AsyncSession

        try:
            project_id = int(project_name)
        except ValueError as e:
            return self._return_failure(message = ResponsesEnum.PROJECT_INVALID_ID.value)

        try:
            async with self.db_client() as session:
                async with session.begin():
                    result = await session.execute(
                        select(Project).where(Project.project_id == project_id)
                    )

                    project = result.scalar_one_or_none()

        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.PROJECT_INNER_ERROR.value)

        
        if project is None:
            project = Project(
                project_id = project_id
            )

            return await self.insert_project(project)

        return self._return_success(project)
        


    async def get_all_projects(self, page: int = 1, page_size: int = 10) -> ObjectModelResult:
        """
        Returns:
            ObjectModelResult:
                if success -> content: dict contains projects & num_pages
                if failure -> error & respone message
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():

                    total_documents = await session.scalar(select(func.count()).select_from(Project))
                    
                    # pages
                    total_pages = total_documents // page_size
                    if total_documents % page_size > 0:
                        total_pages += 1
        
                    skipped_pages = (page - 1) * page_size
                    result = await session.execute(
                        select(Project).offset(skipped_pages).limit(page_size)
                    )
                    projects = list(result.scalars().all())
        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.PROJECT_INNER_ERROR.value)
    
        return self._return_success(content = {
            'projects' : projects, 
            'num_pages': total_pages
        })
