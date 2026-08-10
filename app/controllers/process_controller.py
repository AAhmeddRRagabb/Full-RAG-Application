import os
from .base_controller import BaseController, ControllerResult
from .project_controller import ProjectController

from models.enums import FileExtensionsEnum
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter # cares for spaces and about

class ProcessController(BaseController):
    def __init__(self, project_name: str):
        super().__init__()

        self.project_name = project_name
        self.project_path = ProjectController().get_project_path(project_name = project_name)
        

    def get_file_extension(self, file_name: str):
        """
        Returns:
            ControllerResult:
                if success -> content: file extension
        """

        return os.path.splitext(file_name)[-1]
    
    
    def get_file_loader(self, file_id: str):
        """
        Returns:
            ControllerResult:
                if success -> content: loaded file
                if failure -> content: None
        """

        file_ext = self.get_file_extension(file_name = file_id)
        file_path = os.path.join(self.project_path, file_id)

        if not os.path.exists(file_path):
            return None

        if file_ext == FileExtensionsEnum.FILE_TXT.value:
            return TextLoader(file_path, encoding = 'utf-8')
        
        if file_ext == FileExtensionsEnum.FILE_PDF.value:
            return PyMuPDFLoader(file_path)
        
        return None

    
    
    def get_file_content(self, file_id: str):
        loader = self.get_file_loader(file_id = file_id)

        if loader:
            return loader.load()
    
        return None



    def get_chunks(self, file_content: list, chunk_size: int = 100, overlap_size: int = 100) -> ControllerResult:
        """
        Returns:
            ControllerResult:
                if success -> content: chunks
                if failure -> content: None
        """
        
        # get content
        contents = [data.page_content for data in file_content]
        metadata = [data.metadata for data in file_content]

        # split
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = chunk_size,
            chunk_overlap = overlap_size,
            length_function = len
        )

        chunks = text_splitter.create_documents(
            contents,
            metadatas = metadata
        )

        if chunks: 
            return self._return_success(content = chunks)

        return self._return_failure()
        
        