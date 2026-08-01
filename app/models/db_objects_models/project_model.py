# ----------------------------------------------------
# Building a database model for projects
# ----------------------------------------------------


from .base_obj_model import BaseObjModel
from models.db_schemas import Project
from sqlalchemy import func, select

class ProjectModel(BaseObjModel):
    """
    Data model for the project table
    """
    def __init__(self, db_client):
        super().__init__(db_client)


    @classmethod
    async def create_instance(cls, db_client):
        instance = cls(db_client)
        return instance

    async def insert_project(self, project: Project):
        async with self.db_client() as session:
            async with session.begin():
                session.add(project)

            await session.commit()  
            await session.refresh(project)

        return project
    

    async def get_project_or_insert_it(self, project_name: str) -> Project:
        project_id = int(project_name)

        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(
                    select(Project).where(Project.project_id == project_id)
                )
                project = result.scalar_one_or_none()

                if project is None:
                    project = Project(project_id = project_id)
                    session.add(project)

                return project
    

    async def get_all_projects(self, page: int = 1, page_size: int = 10):
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
    
                return projects, total_pages
