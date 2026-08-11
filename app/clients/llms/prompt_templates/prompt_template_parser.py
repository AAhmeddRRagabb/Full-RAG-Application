import os

from models.enums import ResponsesEnum
from models.system_schemas import ComponentResult


class PromptTemplateParser:
    def __init__(
        self,
        language: str = None,
        default_language: str = "en"
    ):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.default_language = default_language
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
        group: str,
        key: str,
        vars: dict = {}
    ) -> ComponentResult:
        """
        Returns:
            ComponentResult:
                if success -> content: the rendered prompt
                if failure -> error & respone message
        """
        if not group or not key:
            return ComponentResult(
                success = False,
                error = {"group": group, "key": key},
                message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value
            )
        
        targeted_language = self.language
        group_path = os.path.join(self.current_path, "locales", self.language, f"{group}.py")
        if not os.path.exists(group_path):
            group_path = os.path.join(self.current_path, "locales", self.default_language, f"{group}.py" )
            targeted_language = self.default_language

        if not os.path.exists(group_path):
            return ComponentResult(
                success = False,
                error = group_path,
                message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value
            )
        

        module_to_use = __import__(
            f"clients.llms.prompt_templates.locales.{targeted_language}.{group}",
            fromlist = [group]
        )

        if not module_to_use:
            return ComponentResult(
                success = False,
                error = group,
                message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value
            )
        
        try:
            key_attribute: str = getattr(module_to_use, key)
            return ComponentResult(
                success = True,
                content = key_attribute.substitute(vars)
            )
        except Exception as e:
            return ComponentResult(
                success = False,
                error = e,
                message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value
            )
