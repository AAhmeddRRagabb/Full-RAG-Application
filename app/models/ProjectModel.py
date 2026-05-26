# ----------------------------------------------------
# Building a database collection for projects
# ----------------------------------------------------


from .BaseDataModel import BaseDataModel
from .enums.DatabaseEnum import DatabaseEnum
from .db_schemas import Project

class ProjectModel(BaseDataModel):
    """
    Data model for the project collection
    """
    def __init__(self, db_client):
        super().__init__(db_client)
        self.collection = self.db_client[DatabaseEnum.COLLECTION_PROJECTS_NAME.value]


    @classmethod
    async def create_instance(cls, db_client):
        instance = cls(db_client)
        await instance.init_collection_indexes()
        return instance

    async def init_collection_indexes(self):
        indexes = Project.get_indexes()

        for idx in indexes:
            await self.collection.create_index(
                idx["key"],
                name = idx["name"],
                unique = idx["unique"]
            )
            


    async def insert_project(self, project: Project):
        result = await self.collection.insert_one(
            project.model_dump(by_alias = True, exclude_none = True)
        )
        
        project._id = result.inserted_id

        return project
    

    async def get_project_or_insert_it(self, project_id: str):
        record = await self.collection.find_one({
            "project_id" : project_id
        })

        if record is None or not record:
            project = Project(project_id = project_id)
            project = await self.insert_project(project = project)

            return project
        

        return Project(**record)
    

    async def get_all_projects(self, page: int = 1, page_size: int = 10):
        total_documents = await self.collection.count_documents({})

        # pages
        total_pages = total_documents // page_size
        if total_documents % page_size > 0:
            total_pages += 1


        # get all projects [with pagination]
        skipped_pages = (page - 1) * page_size  # skip pages < page
        cursor = self.collection.find().skip(skipped_pages).limit(page_size)
        projects = []

        async for document in cursor:
            projects.append(
                Project(**document)
            )
        
        return projects, total_pages
