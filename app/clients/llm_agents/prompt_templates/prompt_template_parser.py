import os


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
    ):
        """
        Args:
            group: the group of prompts (RAG, ..)
            key  : whether system, documents, or footer prompt.
            vars : the variables used to construct the prompts
        """
        if not group or not key:
            return False
        
        targeted_language = self.language
        group_path = os.path.join(self.current_path, "locales", self.language, f"{group}.py")
        if not os.path.exists(group_path):
            group_path = os.path.join(self.current_path, "locales", self.default_language, f"{group}.py" )
            targeted_language = self.default_language

        if not os.path.exists(group_path):
            return False
        

        module_to_use = __import__(
            f"stores.llm_agents.prompt_templates.locales.{targeted_language}.{group}",
            fromlist = [group]
        )

        if not module_to_use:
            return False
        
        key_attribute: str = getattr(module_to_use, key)
        return key_attribute.substitute(vars)