import os
import logging
from models.enums import ResponsesEnum


class PromptTemplateParser:
    def __init__(
        self,
        language        : str = None,
        default_language: str = "en"
    ):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.default_language = default_language
        self.logger = logging.getLogger("uvicorn")
        self.set_language(language)


    def set_language(self, language: str):
        if not language:
            self.language = self.default_language

        language_path = os.path.join(self.current_path, "locales", language)
        if not os.path.exists(language_path):
            self.language = self.default_language
        else:
            self.language = language


    def get_prompt(
        self,
        task: str,
        key  : str,
        vars : dict = {}
    ) -> str | None:
        """
        Retrieve the required prompt

        Args:
            task (str): the task assigned to the LLM [summarize_doc, summarize_online_search, generate_response]
            key  (str): the prompt to retrieve [system_prompt - task_prompt - footer_prompt]
            vars (str): variables injected into the prompt dynamically

        Returns:
            if success -> the system prompt   
            if failure -> None
        """

        # - get task path
        if not task or not key:
            self.logger.error(f"Error While Getting System Prompt in task | key.\n>>Task: {task}.\n>>Key: {key}")
            return None
        
        targeted_language = self.language
        task_path = os.path.join(self.current_path, "locales", self.language, f"{task}.py")

        if not os.path.exists(task_path):
            task_path = os.path.join(self.current_path, "locales", self.default_language, f"{task}.py" )
            targeted_language = self.default_language

        if not os.path.exists(task_path):
            self.logger.error(f"Error Finding Task Path: {task_path}")
            return None
        

        module_to_use = __import__(
            f"clients.llms.prompt_templates.locales.{targeted_language}.{task}",
            fromlist = [task]
        )

        if not module_to_use:
            self.logger.error(f"Error Finding Prompt Module: {module_to_use}")
            return None


        try:
            key_attribute = getattr(module_to_use, key)
            return key_attribute(**vars)
        
        except Exception as e:
            self.logger.error(f"Error Formatting Prompt: {e}")
            return None

