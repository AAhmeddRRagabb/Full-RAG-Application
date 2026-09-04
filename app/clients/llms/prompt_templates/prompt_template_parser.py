import os
import logging
from models.enums import ResponsesEnum


class PromptTemplateParser:
    def __init__(
        self,
        language: str = None,
        default_language: str = "en"
    ):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.default_language = default_language
        self.set_language(language)
        self.logger = logging.getLogger("uvicorn")


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
        group: str,
        key  : str,
        vars : dict = {}
    ) -> str | None:
        """
        Returns:
            if success -> the system prompt   
            if failure -> None
        """
        if not group or not key:
            self.logger.error(f"Error While Getting System Prompt in group | key.\n>>Group: {group}.\n>>Key: {key}")
            return None
        
        targeted_language = self.language
        group_path = os.path.join(self.current_path, "locales", self.language, f"{group}.py")

        if not os.path.exists(group_path):
            group_path = os.path.join(self.current_path, "locales", self.default_language, f"{group}.py" )
            targeted_language = self.default_language

        if not os.path.exists(group_path):
            self.logger.error(f"Error Finding Group Path: {group_path}")
            return None
        

        module_to_use = __import__(
            f"clients.llms.prompt_templates.locales.{targeted_language}.{group}",
            fromlist = [group]
        )

        if not module_to_use:
            self.logger.error(f"Error Finding Prompt Module: {module_to_use}")
            return None

        try:
            key_attribute: str = getattr(module_to_use, key)
            return key_attribute.substitute(vars)
        
        except Exception as e:
            self.logger.error(f"Error Formatting Prompt: {e}")
            return None

