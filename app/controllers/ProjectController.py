from .BaseController import BaseController
import os


class ProjectController(BaseController):
    def __init__(self):
        super().__init__()

    
    def get_project_path(self, project_name: str):
        project_path = os.path.join(self.assests_files_path, project_name)
        os.makedirs(project_path, exist_ok = True)
        return project_path
    

