from .BaseController import BaseController
from .ProjectController import ProjectController
import os
from models import FileExtensionEnum
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter # cares for spaces and about

class ProcessController(BaseController):
    def __init__(self, project_id: str):
        super().__init__()

        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id = project_id)
        

    def get_file_extension(self, file_name: str):
        return os.path.splitext(file_name)[-1]
    
    
    def get_file_loader(self, file_id: str):
        file_ext = self.get_file_extension(file_name = file_id)

        file_path = os.path.join(self.project_path, file_id)
        if file_ext == FileExtensionEnum.FILE_TXT.value:
            return TextLoader(file_path, encoding = 'utf-8')
        
        if file_ext == FileExtensionEnum.FILE_PDF.value:
            return PyMuPDFLoader(file_path)
        
        return None
    
    
    def get_file_content(self, file_id: str):
        loader = self.get_file_loader(file_id = file_id)
        return loader.load()
    
    def get_chunks(self, file_content: list, chunk_size: int = 100, overlap_size: int = 100):
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

        return chunks

        
        